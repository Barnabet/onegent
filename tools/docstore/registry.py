"""Tool registrations for the `docstore` domain."""

from typing import Optional
from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


class FetchParams(BaseModel):
    query: str = Field(..., description="An id, entity name, or free-text term to match against the doc index.")
    doc_type: Optional[str] = Field(None, description="Optional filter, e.g. 'kyc_dossier', 'credit_input'.")
    latest: bool = Field(True, description="If True (default), return the most recently published match.")


@tool(
    name="docstore.fetch",
    card="cards/fetch.md",
    schema=FetchParams,
    classification="confidential",
    owner="team-platform-ai",
    tags=["docstore", "fetch", "read", "internal-docs"],
)
def fetch(params: FetchParams, ctx: ToolCtx) -> ToolResult:
    return impl.fetch(params, ctx)
