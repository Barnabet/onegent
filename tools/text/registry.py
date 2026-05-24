"""Tool registrations for the `text` domain."""

from typing import List, Optional
from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


class ExtractLinesParams(BaseModel):
    text: str = Field(..., description="The text to scan.")
    kinds: Optional[List[str]] = Field(
        None,
        description="Subset of: 'numeric', 'percentage', 'currency', 'key_value'. Defaults to all four.",
    )


@tool(
    name="text.extract_lines",
    card="cards/extract_lines.md",
    schema=ExtractLinesParams,
    classification="public",
    owner="team-platform-ai",
    tags=["text", "extract", "numeric", "deterministic"],
)
def extract_lines(params: ExtractLinesParams, ctx: ToolCtx) -> ToolResult:
    return impl.extract_lines(params, ctx)


class WordCountParams(BaseModel):
    text: str = Field(..., description="The text to count.")


@tool(
    name="text.word_count",
    card="cards/word_count.md",
    schema=WordCountParams,
    classification="public",
    owner="team-platform-ai",
    tags=["text", "metrics", "deterministic"],
)
def word_count(params: WordCountParams, ctx: ToolCtx) -> ToolResult:
    return impl.word_count(params, ctx)
