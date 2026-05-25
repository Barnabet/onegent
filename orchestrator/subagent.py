"""
The sub-agent model loop. Runs inside a worker process.

Loop: send messages+tools to the LLM → if tool_calls, execute each one,
append the results, repeat. Emits events on the provided emit() callback so
the worker can forward them to the supervisor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from runtime import llm, tool_registry, worker_proto
from runtime.pack_loader import BoundPack
from runtime.tool_registry import ToolCtx


def _extract_output_paths(data: dict) -> List[str]:
    """Return the set of disk paths a tool just wrote to.

    Tools in this repo report their outputs in one of two shapes:
      - ``data["output"]`` — a single path string (xlsx/pdf write tools).
      - ``data["outputs"]`` — a list of path strings (xlsx.convert per-sheet,
        future multi-file emitters).
    Anything else is ignored on purpose: we don't want to attach random
    string fields that happen to look path-shaped.
    """
    out: List[str] = []
    single = data.get("output")
    if isinstance(single, str) and single:
        out.append(single)
    many = data.get("outputs")
    if isinstance(many, list):
        out.extend(p for p in many if isinstance(p, str) and p)
    return out


@dataclass
class RunStats:
    tool_calls: int = 0
    turns: int = 0
    final_finish_reason: str = "stop"


def build_system_prompt(
    bound: BoundPack,
    files: Optional[List[dict]] = None,
    allowed_packs: Optional[List[str]] = None,
) -> str:
    """Compose the system prompt: a header + each skill's body, plus any
    conversation-scoped file attachments the user has uploaded.

    When `allowed_packs` is non-None (router runs), the prompt also inlines
    the catalog of delegatable packs and the full on-disk skill catalog, so
    the router does not need to spend tool calls on list_packs / list_skills.
    """
    parts: List[str] = []
    parts.append(
        "You are a CIB Gen-AI sub-agent. Follow the loaded skills exactly. "
        "Use the provided tools by name; do not invent tools. When a skill's "
        "workflow tells you to call a tool, call it. Be concise. "
        "Prioritize parallel tool calls: whenever you need multiple tool "
        "calls that do not depend on each other's outputs, issue them "
        "together in a single response rather than sequentially."
    )
    parts.append("")
    parts.append(f"Pack: {bound.pack.name} (v{bound.pack.version})")
    parts.append(f"Pack description: {bound.pack.description}")
    parts.append("")
    if files:
        parts.append(f"Files available in this conversation ({len(files)}):")
        for f in files:
            parts.append(
                f"  - {f.get('name')} ({f.get('mime')}, {f.get('size')} bytes) "
                f"@ {f.get('path')} [id={f.get('file_id')}]"
            )
        parts.append("")
        # Only hint about file-reading tools that are actually bound to this
        # pack; otherwise the model will try to call tools that don't exist.
        file_tool_prefixes = ("pdf.", "xlsx.", "excel.", "docx.", "pptx.")
        file_tools = [t for t in bound.tools if t.startswith(file_tool_prefixes)]
        if file_tools:
            parts.append(
                "Use the file `path` with the file-reading tools available to "
                f"this pack ({', '.join(sorted(file_tools))}). Do not invent paths."
            )
        else:
            parts.append(
                "This pack has no file-reading tools of its own. If the user's "
                "request needs the contents of an attached file, delegate to a "
                "specialist that can read it."
            )
        parts.append("")

    # Router-only: inline the pack + skill catalogs so the orchestrator can
    # reason about delegation natively, without spending tool calls on
    # list_packs / list_skills.
    if allowed_packs is not None:
        from runtime.pack_loader import load as load_pack
        from runtime.skill_loader import catalog as skill_catalog

        parts.append(f"Delegatable packs ({len(allowed_packs)}):")
        if not allowed_packs:
            parts.append("  (none — only skills-only delegation is available)")
        for name in allowed_packs:
            try:
                p = load_pack(name)
                parts.append(f"  - {p.name} [{p.classification}] — {p.description}")
            except Exception as e:
                parts.append(f"  - {name} (load failed: {e})")
        parts.append("")

        try:
            cat = skill_catalog()
        except Exception:
            cat = []
        parts.append(f"Composable skills ({len(cat)}):")
        for s in cat:
            parts.append(f"  - {s.name} — {s.description}")
        parts.append("")

    parts.append(f"Loaded skills ({len(bound.skills)}):")
    for s in bound.skills:
        parts.append("")
        parts.append(f"================ SKILL: {s.frontmatter.name} ================")
        parts.append(s.body.strip())
    return "\n".join(parts)


def build_tool_specs(bound: BoundPack) -> List[dict]:
    """Convert each bound tool into the {name, description, schema} shape the llm client wants."""
    specs: List[dict] = []
    for tool_name in bound.tools:
        entry = tool_registry.get(tool_name)
        specs.append(
            {
                "name": entry.name,
                "description": entry.card_body,
                "schema": entry.json_schema(),
            }
        )
    return specs


def run(
    bound: BoundPack,
    user_message: str,
    ctx: ToolCtx,
    emit: Callable[[dict], None],
    history: Optional[List[dict]] = None,
) -> RunStats:
    """Run the sub-agent loop to completion. Returns stats; emits events.

    `history` is an optional list of prior `{role, content}` messages
    (user/assistant pairs) to prepend before `user_message`. Used by the
    server to give the router conversation memory across runs. Sub-agents
    don't receive history — each delegation is self-contained.
    """
    system = build_system_prompt(bound, files=ctx.files, allowed_packs=ctx.allowed_packs)
    tools = build_tool_specs(bound)

    messages: List[dict] = list(history or [])
    messages.append({"role": "user", "content": user_message})
    stats = RunStats()
    max_calls = bound.pack.limits.max_tool_calls_per_run

    while True:
        stats.turns += 1
        resp = llm.chat(messages=messages, tools=tools, model=bound.pack.model, system=system)
        stats.final_finish_reason = resp.finish_reason

        if resp.text:
            emit(worker_proto.model_text(resp.text))

        if not resp.has_tool_calls:
            return stats

        messages.append(llm.assistant_message_from_response(resp))

        for tc in resp.tool_calls:
            stats.tool_calls += 1
            if stats.tool_calls > max_calls:
                raise RuntimeError(
                    f"Exceeded max_tool_calls_per_run ({max_calls})"
                )
            emit(worker_proto.tool_call(tc.name, tc.arguments, tc.id))
            result = tool_registry.call(tc.name, tc.arguments, ctx)
            payload_dict = result.model_dump()
            # Strip image bytes from the audit/result event — they're large
            # and the model receives them via the follow-up user message.
            event_payload = dict(payload_dict)
            if event_payload.get("images"):
                event_payload["images"] = [
                    {"mime": i.get("mime"), "label": i.get("label"), "bytes": len(i.get("b64") or "")}
                    for i in event_payload["images"]
                ]
            emit(
                worker_proto.tool_result(
                    name=tc.name,
                    call_id=tc.id,
                    ok=result.ok,
                    payload=event_payload,
                )
            )
            # If the tool wrote one or more files to disk, emit `file_created`
            # events so the parent process can attach them to the conversation
            # and the UI's Files sidebar can pick them up. We just announce
            # the paths; the parent validates / registers / re-emits.
            if result.ok and isinstance(result.data, dict):
                for path in _extract_output_paths(result.data):
                    emit(worker_proto.file_created(
                        path=path,
                        tool_name=tc.name,
                        call_id=tc.id,
                        conversation_id=ctx.conversation_id,
                    ))
            # The tool-protocol message itself stays text-only (some providers
            # reject image parts inside a `tool` role message).
            tool_text_payload = {k: v for k, v in payload_dict.items() if k != "images"}
            messages.append(llm.tool_result_message(tc.id, json.dumps(tool_text_payload)))
            # If the tool returned inline images, surface them in a follow-up
            # user message so the model can actually see them on the next turn.
            if result.images:
                messages.append(
                    llm.user_message_with_images(
                        text=f"Inline images returned by tool `{tc.name}`:",
                        images=[i.model_dump() for i in result.images],
                    )
                )
