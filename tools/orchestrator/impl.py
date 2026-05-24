"""Implementations for the `orchestrator` tool domain.

These tools let a *router pack* dispatch work to other ("specialist")
packs. They are useful only when the surrounding worker has populated
`ToolCtx.allowed_packs` and `ToolCtx.emit` — i.e. when the running pack
is intended as a router.

Specialists run in-process inside the same worker (no extra OS process):
we just call `orchestrator.subagent.run()` with a fresh `BoundPack`.
This keeps audit logs unified and avoids spawn-on-spawn complexity.
"""

from __future__ import annotations

import traceback
from dataclasses import replace

from runtime import tool_registry
from runtime.pack_loader import bind, load as load_pack
from runtime.tool_registry import ToolCtx, ToolError, ToolResult


def list_packs(params, ctx: ToolCtx) -> ToolResult:
    if ctx.allowed_packs is None:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="no_router_context",
                message="orchestrator.list_packs called outside a router run.",
            ),
        )
    items = []
    for name in ctx.allowed_packs:
        try:
            pack = load_pack(name)
        except Exception as e:
            items.append({"name": name, "description": f"(load failed: {e})", "classification": "unknown"})
            continue
        items.append(
            {
                "name": pack.name,
                "description": pack.description,
                "classification": pack.classification,
            }
        )
    return ToolResult(ok=True, data={"packs": items})


def delegate(params, ctx: ToolCtx) -> ToolResult:
    # Local import to avoid an import cycle (orchestrator.subagent imports
    # tool_registry; this tool module is imported via tool_registry.discover).
    from orchestrator import subagent as _subagent

    if ctx.allowed_packs is None:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="no_router_context",
                message="orchestrator.delegate called outside a router run.",
            ),
        )
    if params.pack not in ctx.allowed_packs:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="pack_not_allowed",
                message=(
                    f"Pack {params.pack!r} is not in the allowed list "
                    f"({sorted(ctx.allowed_packs)}). Pick one of those."
                ),
            ),
        )

    try:
        pack = load_pack(params.pack)
        bound = bind(pack)
    except FileNotFoundError as e:
        return ToolResult(
            ok=False,
            error=ToolError(code="pack_not_found", message=str(e)),
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            error=ToolError(code="pack_load_failed", message=str(e)),
        )

    # Build a child ToolCtx scoped to the specialist pack. It inherits the
    # router's audit + emit so all sub-events are visible to the supervisor.
    child_ctx = replace(
        ctx,
        pack_name=pack.name,
        classification_ceiling=pack.classification,
        allowed_data_sources=pack.allowed_data_sources,
        allowed_packs=None,  # specialists cannot themselves delegate
    )

    # Tag inner events so the UI can group them under this delegate call.
    parent_emit = ctx.emit
    final_text_parts = []

    def inner_emit(event: dict) -> None:
        tagged = {**event, "subagent_of": params.pack}
        if parent_emit is not None:
            parent_emit(tagged)
        if ctx.audit is not None:
            ctx.audit(
                event["type"],
                **{k: v for k, v in tagged.items() if k != "type"},
            )
        if event.get("type") == "model_text":
            final_text_parts.append(event.get("delta", ""))

    try:
        stats = _subagent.run(bound, params.message, child_ctx, inner_emit)
    except Exception as e:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="subagent_failed",
                message=f"{e}\n{traceback.format_exc()}",
            ),
        )

    return ToolResult(
        ok=True,
        data={
            "pack": pack.name,
            "final_text": final_text_parts[-1] if final_text_parts else "",
            "stats": {
                "turns": stats.turns,
                "tool_calls": stats.tool_calls,
                "finish_reason": stats.final_finish_reason,
            },
        },
    )
