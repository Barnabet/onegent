"""
FastAPI app exposing the agents library over HTTP for the webui.

Run with:
  uvicorn server.app:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from evals import case as case_mod
from runtime import pack_loader, skill_loader, tool_registry
from server import conversations as conv_store, eval_jobs, files as files_store, runs


REPO = Path(__file__).resolve().parent.parent
AUDIT_DIR = Path(os.environ.get("AUDIT_DIR", REPO / "audit_logs"))


# ---------------------------------------------------------------------------
# App + one-time discovery
# ---------------------------------------------------------------------------


app = FastAPI(title="CIB Agents API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-only; tighten before any real deployment.
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _discover_tools_once() -> None:
    tool_registry.discover()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "tools": len(tool_registry.all_tools())}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@app.get("/api/tools")
def list_tools() -> List[dict]:
    return [
        {
            "name": t.name,
            "classification": t.classification,
            "owner": t.owner,
            "tags": t.tags,
            "version": t.version,
        }
        for t in tool_registry.all_tools()
    ]


@app.get("/api/tools/{name}")
def get_tool(name: str) -> dict:
    if not tool_registry.has(name):
        raise HTTPException(404, f"Tool {name!r} not found")
    t = tool_registry.get(name)
    return {
        "name": t.name,
        "classification": t.classification,
        "owner": t.owner,
        "tags": t.tags,
        "version": t.version,
        "card": t.card_body,
        "schema": t.json_schema(),
    }


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


@app.get("/api/skills")
def list_skills() -> List[dict]:
    return [
        {"name": s.name, "description": s.description, "version": s.version}
        for s in skill_loader.catalog()
    ]


@app.get("/api/skills/{name}")
def get_skill(name: str) -> dict:
    try:
        s = skill_loader.load(name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return {
        "name": s.frontmatter.name,
        "description": s.frontmatter.description,
        "version": s.frontmatter.version,
        "body": s.body,
        "manifest": asdict(s.manifest),
    }


# ---------------------------------------------------------------------------
# Packs
# ---------------------------------------------------------------------------


def _list_pack_names() -> List[str]:
    root = pack_loader.packs_root()
    if not root.is_dir():
        return []
    return sorted(p.stem for p in root.glob("*.yaml"))


def _default_allowed_packs() -> List[str]:
    """All packs except the router itself, used when the client doesn't pick."""
    return [n for n in _list_pack_names() if n != "router"]


@app.get("/api/packs")
def list_packs() -> List[dict]:
    out = []
    for name in _list_pack_names():
        try:
            p = pack_loader.load(name)
        except Exception as e:
            out.append({"name": name, "error": str(e)})
            continue
        out.append({
            "name": p.name,
            "version": p.version,
            "owner": p.owner,
            "description": p.description,
            "skills": p.skills,
            "classification": p.classification,
            "model": p.model,
        })
    return out


@app.get("/api/packs/{name}")
def get_pack(name: str) -> dict:
    try:
        p = pack_loader.load(name)
        bound = pack_loader.bind(p)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, str(e))
    return {
        "name": p.name,
        "version": p.version,
        "owner": p.owner,
        "description": p.description,
        "classification": p.classification,
        "allowed_data_sources": p.allowed_data_sources,
        "model": p.model,
        "limits": asdict(p.limits),
        "skills": [
            {"name": s.frontmatter.name, "description": s.frontmatter.description}
            for s in bound.skills
        ],
        "tools": bound.tools,
        "effective_classification": bound.effective_classification,
    }


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


class StartRunBody(BaseModel):
    user_message: str
    user_id: Optional[str] = "webui"
    # Conversation this run is a turn of. When set, the server loads the
    # conversation's transcript as `history` for the worker and appends
    # the user message + the assistant's final reply on completion. The
    # conversation's attached files are forwarded automatically; `files`
    # below is then ignored. The chat UI always sets this.
    conversation_id: Optional[str] = None
    # Specialist packs the orchestrator is allowed to delegate to. The router
    # pack itself is implicit. If omitted, defaults to every non-router pack
    # the server can discover.
    allowed_packs: Optional[List[str]] = None
    # Escape hatch for tools/tests: pin the run to a specific pack instead of
    # going through the router. The web UI does not use this.
    pack: Optional[str] = None
    # File metadata to forward when no conversation_id is provided (evals,
    # direct API). Ignored when conversation_id is set.
    files: Optional[List[dict]] = None


def _run_to_dict(r: "runs.LiveRun") -> dict:
    return {
        "run_id": r.run_id,
        "pack": r.pack,
        "user_message": r.user_message,
        "user_id": r.user_id,
        "started_at": r.started_at,
        "status": r.status,
        "error": r.error,
        "final_text": r.final_text,
        "stats": r.stats,
        "events_count": len(r.events),
    }


@app.post("/api/runs")
async def start_run(body: StartRunBody) -> dict:
    loop = asyncio.get_running_loop()

    # Resolve conversation context (history + files) if a conversation_id is
    # provided. The chat UI always provides one; evals / direct callers may not.
    history: Optional[List[dict]] = None
    files: Optional[List[dict]] = body.files
    conv_id = body.conversation_id
    on_done = None
    if conv_id:
        c = conv_store.get(conv_id)
        if c is None:
            raise HTTPException(404, f"Conversation {conv_id!r} not found")
        history = conv_store.history_for_llm(conv_id)
        # Forward every file currently attached to the conversation; the
        # user-provided `files` field is ignored to keep one source of truth.
        files = [
            files_store.to_dict(m)
            for fid in c.file_ids
            if (m := files_store.get(fid)) is not None
        ]
        # Record the user turn now, the assistant reply on run completion.
        conv_store.append_message(conv_id, "user", body.user_message)

        def on_done(r: "runs.LiveRun") -> None:
            if r.status == "done" and r.final_text:
                conv_store.append_message(
                    conv_id, "assistant", r.final_text, run_id=r.run_id
                )

    if body.pack:
        # Direct-to-pack escape hatch.
        run = runs.start_run(
            body.pack,
            body.user_message,
            body.user_id or "webui",
            loop=loop,
            history=history,
            files=files,
            conversation_id=conv_id,
            on_done=on_done,
        )
    else:
        # Default path: go through the router.
        allowed = body.allowed_packs
        if allowed is None:
            allowed = _default_allowed_packs()
        run = runs.start_run(
            "router",
            body.user_message,
            body.user_id or "webui",
            loop=loop,
            allowed_packs=allowed,
            history=history,
            files=files,
            conversation_id=conv_id,
            on_done=on_done,
        )
    return _run_to_dict(run)


@app.get("/api/runs")
def list_runs() -> List[dict]:
    """Live + completed in-memory runs, plus any persisted audit logs on disk."""
    live = [_run_to_dict(r) for r in runs.all_runs()]
    seen = {r["run_id"] for r in live}
    if AUDIT_DIR.is_dir():
        for path in sorted(AUDIT_DIR.glob("run_*.jsonl"), reverse=True):
            rid = path.stem
            if rid in seen:
                continue
            try:
                first = path.open("r", encoding="utf-8").readline()
                meta = json.loads(first) if first else {}
            except Exception:
                meta = {}
            live.append({
                "run_id": rid,
                "pack": meta.get("pack", "?"),
                "user_id": meta.get("user_id", "?"),
                "user_message": meta.get("user_message", ""),
                "started_at": meta.get("ts", 0),
                "status": "persisted",
                "error": None,
                "final_text": "",
                "stats": None,
                "events_count": 0,
            })
    return sorted(live, key=lambda r: r["started_at"] or 0, reverse=True)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = runs.get(run_id)
    if run is not None:
        d = _run_to_dict(run)
        d["events"] = run.events
        return d
    # Fall back to disk.
    path = AUDIT_DIR / f"{run_id}.jsonl"
    if not path.is_file():
        raise HTTPException(404, f"Run {run_id!r} not found")
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {"run_id": run_id, "status": "persisted", "events": lines}


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id!r} not found")
    q = await runs.subscribe(run)

    async def gen():
        try:
            while True:
                ev = await q.get()
                if ev.get("type") == "__end__":
                    # Send a final marker with the run's summary.
                    yield {"event": "done", "data": json.dumps(_run_to_dict(run))}
                    return
                yield {"event": ev.get("type", "message"), "data": json.dumps(ev, default=str)}
        finally:
            runs.unsubscribe(run, q)

    return EventSourceResponse(gen())


# ---------------------------------------------------------------------------
# Files (conversation attachments)
# ---------------------------------------------------------------------------


@app.post("/api/files")
async def upload_file(
    conversation_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    if conv_store.get(conversation_id) is None:
        raise HTTPException(404, f"Conversation {conversation_id!r} not found")
    data = await file.read()
    meta = files_store.save(
        conversation_id=conversation_id,
        name=file.filename or "file",
        mime=file.content_type or "application/octet-stream",
        data=data,
    )
    conv_store.attach_file(conversation_id, meta.file_id)
    return files_store.to_dict(meta)


@app.get("/api/files")
def list_files(conversation_id: str) -> List[dict]:
    return [files_store.to_dict(m) for m in files_store.list_for(conversation_id)]


@app.delete("/api/files/{file_id}")
def delete_file(file_id: str) -> dict:
    meta = files_store.get(file_id)
    if meta is None:
        raise HTTPException(404, f"File {file_id!r} not found")
    conv_store.detach_file(meta.conversation_id, file_id)
    files_store.delete(file_id)
    return {"ok": True}


@app.get("/api/files/{file_id}/download")
def download_file(file_id: str) -> FileResponse:
    meta = files_store.get(file_id)
    if meta is None:
        raise HTTPException(404, f"File {file_id!r} not found")
    path = Path(meta.path)
    if not path.is_file():
        raise HTTPException(410, f"File {file_id!r} no longer on disk")
    return FileResponse(
        path=str(path),
        filename=meta.name,
        media_type=meta.mime or "application/octet-stream",
    )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class CreateConversationBody(BaseModel):
    title: Optional[str] = None


class RenameConversationBody(BaseModel):
    title: str


@app.get("/api/conversations")
def list_conversations() -> List[dict]:
    return [conv_store.summary_dict(c) for c in conv_store.list_all()]


@app.post("/api/conversations")
def create_conversation(body: CreateConversationBody) -> dict:
    c = conv_store.create(title=body.title)
    return conv_store.to_dict(c)


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str) -> dict:
    c = conv_store.get(conv_id)
    if c is None:
        raise HTTPException(404, f"Conversation {conv_id!r} not found")
    d = conv_store.to_dict(c)
    # Inline the file metadata so the UI doesn't need a second round-trip.
    d["files"] = [
        files_store.to_dict(m)
        for fid in c.file_ids
        if (m := files_store.get(fid)) is not None
    ]
    return d


@app.patch("/api/conversations/{conv_id}")
def rename_conversation(conv_id: str, body: RenameConversationBody) -> dict:
    c = conv_store.rename(conv_id, body.title)
    if c is None:
        raise HTTPException(404, f"Conversation {conv_id!r} not found")
    return conv_store.to_dict(c)


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str) -> dict:
    c = conv_store.get(conv_id)
    if c is None:
        raise HTTPException(404, f"Conversation {conv_id!r} not found")
    # Delete attached files too.
    for fid in list(c.file_ids):
        files_store.delete(fid)
    conv_store.delete(conv_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Evals
# ---------------------------------------------------------------------------


@app.get("/api/evals/cases")
def list_eval_cases() -> List[dict]:
    out = []
    for c in case_mod.discover_cases():
        out.append({
            "id": c.id,
            "pack": c.pack,
            "description": c.description,
            "user_message": c.user_message,
            "timeout": c.timeout,
            "assertions": [
                {**{"kind": getattr(a, "kind", "?")},
                 **{k: v for k, v in vars(a).items() if k != "kind"}}
                for a in c.assertions
            ],
            "source_path": str(c.source_path) if c.source_path else None,
        })
    return out


class StartEvalBody(BaseModel):
    pack: Optional[str] = None
    case: Optional[str] = None
    use_judge: bool = True


def _job_to_dict(j: "eval_jobs.LiveEvalJob") -> dict:
    return {
        "job_id": j.job_id,
        "pack": j.pack,
        "case": j.case,
        "use_judge": j.use_judge,
        "started_at": j.started_at,
        "status": j.status,
        "error": j.error,
        "case_results": j.case_results,
    }


@app.post("/api/evals/run")
async def start_eval(body: StartEvalBody) -> dict:
    loop = asyncio.get_running_loop()
    job = eval_jobs.start_job(body.pack, body.case, body.use_judge, loop=loop)
    return _job_to_dict(job)


@app.get("/api/evals/jobs")
def list_eval_jobs() -> List[dict]:
    return [_job_to_dict(j) for j in eval_jobs.all_jobs()]


@app.get("/api/evals/jobs/{job_id}")
def get_eval_job(job_id: str) -> dict:
    j = eval_jobs.get(job_id)
    if j is None:
        raise HTTPException(404, f"Eval job {job_id!r} not found")
    return _job_to_dict(j)


@app.get("/api/evals/jobs/{job_id}/stream")
async def stream_eval_job(job_id: str):
    j = eval_jobs.get(job_id)
    if j is None:
        raise HTTPException(404, f"Eval job {job_id!r} not found")
    q = await eval_jobs.subscribe(j)

    async def gen():
        try:
            while True:
                ev = await q.get()
                if ev.get("type") == "__end__":
                    yield {"event": "done", "data": json.dumps(_job_to_dict(j))}
                    return
                yield {"event": ev.get("type", "message"), "data": json.dumps(ev, default=str)}
        finally:
            eval_jobs.unsubscribe(j, q)

    return EventSourceResponse(gen())


@app.get("/api/evals/results")
def list_eval_results() -> List[dict]:
    base = REPO / "evals" / "results"
    if not base.is_dir():
        return []
    out = []
    for path in sorted(base.glob("*.jsonl"), reverse=True):
        try:
            lines = [
                json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()
            ]
        except Exception:
            lines = []
        passed = sum(1 for r in lines if r.get("passed"))
        out.append({
            "file": path.name,
            "total": len(lines),
            "passed": passed,
            "cases": lines,
        })
    return out
