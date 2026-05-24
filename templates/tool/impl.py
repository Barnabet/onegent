"""
Tool implementation template.

Keep this file:
  - stateless (no module-level mutable state).
  - import-safe (no network / disk side effects at import time).
  - free of LLM calls (a tool that needs the LLM is a *skill*, not a tool).
"""

from runtime.tool_registry import ToolCtx, ToolResult, ToolError


def do_the_thing(params, ctx: ToolCtx) -> ToolResult:
    # ---- happy path ----
    # result = some_pure_python_work(params.target, params.option)
    # return ToolResult(ok=True, data={"result": result})

    # ---- error path (no raise — return envelope) ----
    # return ToolResult(
    #     ok=False,
    #     error=ToolError(
    #         code="not_found",
    #         message="The target was not found.",
    #         retriable=False,
    #     ),
    # )

    raise NotImplementedError("Replace the template body with the real implementation.")
