"""Tool registrations for the `core` domain."""

from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


class EchoParams(BaseModel):
    text: str = Field(..., description="A short string to echo back verbatim.")


@tool(
    name="core.echo",
    card="cards/echo.md",
    schema=EchoParams,
    classification="public",
    owner="team-platform-ai",
    tags=["diagnostic", "smoke-test"],
)
def echo(params: EchoParams, ctx: ToolCtx) -> ToolResult:
    return impl.echo(params, ctx)
