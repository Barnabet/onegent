"""Tool registrations for the `xlsx` domain."""

from typing import Optional
from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


class ReadParams(BaseModel):
    path: str = Field(..., description="Path to .xlsx, .xlsm, .csv, or .tsv file.")
    sheet: Optional[str] = Field(None, description="Sheet name (xlsx only). Defaults to the first sheet.")
    has_header: bool = Field(True, description="If true, treat the first row as column headers.")


@tool(
    name="xlsx.read",
    card="cards/read.md",
    schema=ReadParams,
    classification="internal",
    owner="team-doc-ai",
    tags=["spreadsheet", "read", "tabular"],
)
def read(params: ReadParams, ctx: ToolCtx) -> ToolResult:
    return impl.read(params, ctx)
