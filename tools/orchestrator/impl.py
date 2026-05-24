"""Implementations for the `orchestrator` tool domain.

This module exposes the `orchestrator.delegate` tool. It is useful only
when the surrounding worker has populated `ToolCtx.allowed_packs` and
`ToolCtx.emit` — i.e. when the running pack is the router. The router's
system prompt inlines the pack + skill catalogs natively, so it does not
need separate listing tools.

Three delegation shapes are supported:

  1. **pack only** — pass `pack`; the specialist runs with that pack's
     own skill list. The classic "route to credit_analyst" case.
  2. **pack + extra_skills** — pass `pack` and `extra_skills`; the pack's
     skills are unioned with the extras. Lets the router top up a
     specialist with e.g. `pdf_handling` without baking it into the
     pack YAML.
  3. **skills only** — pass `skills` (no `pack`); an ad-hoc sub-agent is
     spawned with that skill list and the router's own pack identity
     (model, classification, data sources, limits).

There is no per-run skill allow-list — the router is trusted to compose
any skill into a sub-agent. What the router itself may invoke is
constrained separately, by the router pack's own `skills:` list (and the
tools those skills require), not by anything here.

Specialists run in-process inside the same worker (no extra OS process):
we just call `orchestrator.subagent.run()` with a fresh `BoundPack`. This
keeps audit logs unified and avoids spawn-on-spawn complexity.
"""

from __future__ import annotations

import traceback
from dataclasses import replace

from runtime.pack_loader import bind, bind_skills, load as load_pack
from runtime.tool_registry import ToolCtx, ToolError, ToolResult


def _err(code: str, message: str) -> ToolResult:
    return ToolResult(ok=False, error=ToolError(code=code, message=message))


def delegate(params, ctx: ToolCtx) -> ToolResult:
    # Local import to avoid an import cycle (orchestrator.subagent imports
    # tool_registry; this tool module is imported via tool_registry.discover).
    from orchestrator import subagent as _subagent

    if ctx.allowed_packs is None:
        return _err(
            "no_router_context",
            "orchestrator.delegate called outside a router run.",
        )

    # --- Validate which delegation shape we're in ---------------------------
    has_pack = bool(params.pack)
    has_skills = params.skills is not None and len(params.skills) > 0
    extra_skills = params.extra_skills or []

    if has_pack and has_skills:
        return _err(
            "invalid_input",
            "Pass either `pack` or `skills`, not both. Use `extra_skills` "
            "to splice skills on top of a pack.",
        )
    if not has_pack and not has_skills:
        return _err(
            "invalid_input",
            "Pass `pack` (delegate to a specialist) or `skills` "
            "(ad-hoc sub-agent). Neither was provided.",
        )
    if not has_pack and extra_skills:
        return _err(
            "invalid_input",
            "`extra_skills` only makes sense with a `pack`. For a "
            "skills-only sub-agent, put every skill in `skills`.",
        )

    # --- Enforce pack allow-list --------------------------------------------
    if has_pack and params.pack not in ctx.allowed_packs:
        return _err(
            "pack_not_allowed",
            f"Pack {params.pack!r} is not in the allowed list "
            f"({sorted(ctx.allowed_packs)}). Pick one of those.",
        )

    # --- Build the BoundPack -------------------------------------------------
    try:
        if has_pack:
            pack = load_pack(params.pack)
            if extra_skills:
                merged = list(pack.skills) + [s for s in extra_skills if s not in pack.skills]
                bound = bind_skills(merged, identity=pack)
            else:
                bound = bind(pack)
            child_identity = pack
            sub_label = pack.name
        else:
            # Skills-only ad-hoc sub-agent. Inherit identity from the router's
            # own pack (the worker's current pack), so the model / ceiling /
            # data sources / limits are exactly what the router runs under.
            parent_pack = load_pack(ctx.pack_name)
            bound = bind_skills(list(params.skills or []), identity=parent_pack)
            child_identity = parent_pack
            sub_label = f"skills:{','.join(params.skills or [])}"
    except FileNotFoundError as e:
        return _err("pack_not_found" if has_pack else "skill_not_found", str(e))
    except Exception as e:
        return _err("pack_load_failed" if has_pack else "skills_bind_failed", str(e))

    # --- File scoping --------------------------------------------------------
    # Resolve which files to forward to the specialist. If the router did
    # not specify, forward every attached file (back-compat). If it passed
    # an explicit list (including empty), filter accordingly. Unknown ids
    # are silently dropped.
    if params.files is None:
        forwarded_files = ctx.files
    else:
        wanted = set(params.files)
        forwarded_files = [
            f for f in (ctx.files or []) if f.get("file_id") in wanted
        ]

    # Build a child ToolCtx scoped to the specialist pack. It inherits the
    # router's audit + emit so all sub-events are visible to the supervisor.
    child_ctx = replace(
        ctx,
        pack_name=child_identity.name,
        classification_ceiling=child_identity.classification,
        allowed_data_sources=child_identity.allowed_data_sources,
        allowed_packs=None,   # specialists cannot themselves delegate
        files=forwarded_files,
    )

    # Tag inner events so the UI can group them under this delegate call.
    parent_emit = ctx.emit
    final_text_parts = []

    def inner_emit(event: dict) -> None:
        tagged = {**event, "subagent_of": sub_label}
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
        return _err(
            "subagent_failed",
            f"{e}\n{traceback.format_exc()}",
        )

    return ToolResult(
        ok=True,
        data={
            "pack": params.pack,
            "skills": [s.frontmatter.name for s in bound.skills],
            "final_text": final_text_parts[-1] if final_text_parts else "",
            "stats": {
                "turns": stats.turns,
                "tool_calls": stats.tool_calls,
                "finish_reason": stats.final_finish_reason,
            },
        },
    )
