"""Tool registrations for the `orchestrator` domain."""

from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


class ListPacksParams(BaseModel):
    pass


class DelegateParams(BaseModel):
    pack: str = Field(..., description="Name of the specialist pack to delegate to.")
    message: str = Field(
        ...,
        description=(
            "Self-contained sub-task for the specialist. Include all context "
            "it needs; it cannot see the parent conversation."
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
    name="orchestrator.delegate",
    card="cards/delegate.md",
    schema=DelegateParams,
    classification="public",
    owner="team-platform-ai",
    tags=["routing", "meta"],
)
def delegate(params: DelegateParams, ctx: ToolCtx) -> ToolResult:
    return impl.delegate(params, ctx)
