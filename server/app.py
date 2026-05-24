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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from evals import case as case_mod
from runtime import pack_loader, skill_loader, tool_registry
from server import eval_jobs, runs


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
    pack: str
    user_message: str
    user_id: Optional[str] = "webui"


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
    run = runs.start_run(body.pack, body.user_message, body.user_id or "webui", loop=loop)
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
