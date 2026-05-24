"""Tool registrations for the `orchestrator` domain."""

from typing import List, Optional

from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


class ListPacksParams(BaseModel):
    pass


class ListSkillsParams(BaseModel):
    pass


class DelegateParams(BaseModel):
    pack: Optional[str] = Field(
        default=None,
        description=(
            "Name of a specialist pack to delegate to. Must be in "
            "`allowed_packs`. Omit to spawn an ad-hoc sub-agent built "
            "from `skills` alone."
        ),
    )
    skills: Optional[List[str]] = Field(
        default=None,
        description=(
            "Skills to bind on an ad-hoc sub-agent when no `pack` is given. "
            "Picked from `orchestrator.list_skills` (the full on-disk catalog). "
            "Exactly one of `pack` or `skills` must be set."
        ),
    )
    extra_skills: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional skills to splice on top of the chosen `pack`'s own "
            "skill list. Picked from `orchestrator.list_skills`. Ignored "
            "when `pack` is omitted (use `skills` instead). Skills already "
            "in the pack are deduplicated."
        ),
    )
    message: str = Field(
        ...,
        description=(
            "Self-contained sub-task for the specialist. Include all context "
            "it needs; it cannot see the parent conversation."
        ),
    )
    files: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional list of conversation `file_id`s to forward to the "
            "specialist. Omit (or pass null) to forward every attached file; "
            "pass an empty list to forward none; pass a subset to forward only "
            "those. Unknown ids are ignored."
        ),
    )


@tool(
    name="orchestrator.list_packs",
    card="cards/list_packs.md",
    schema=ListPacksParams,
    classification="public",
    owner="team-platform-ai",
    tags=["routing", "meta"],
)
def list_packs(params: ListPacksParams, ctx: ToolCtx) -> ToolResult:
    return impl.list_packs(params, ctx)


@tool(
    name="orchestrator.list_skills",
    card="cards/list_skills.md",
    schema=ListSkillsParams,
    classification="public",
    owner="team-platform-ai",
    tags=["routing", "meta"],
)
def list_skills(params: ListSkillsParams, ctx: ToolCtx) -> ToolResult:
    return impl.list_skills(params, ctx)


@tool(
    name="orchestrator.delegate",
    card="cards/delegate.md",
    schema=DelegateParams,
    classification="public",
    owner="team-platform-ai",
    tags=["routing", "meta"],
)
def delegate(params: DelegateParams, ctx: ToolCtx) -> ToolResult:
    return impl.delegate(params, ctx)
