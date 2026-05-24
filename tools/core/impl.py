"""Implementations for tools in the `core` domain."""

from runtime.tool_registry import ToolCtx, ToolResult


def echo(params, ctx: ToolCtx) -> ToolResult:
    return ToolResult(ok=True, data={"echoed": params.text})
