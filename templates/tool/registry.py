"""
Tool registration template.

Copy this folder to `tools/<your_domain>/` and:
  1. Rename the parameter model and function.
  2. Edit the @tool() metadata (name, card path, classification, owner, tags).
  3. Implement the function in impl.py.
  4. Write the card in cards/<your_tool>.md.
  5. Add tests in tests/.

See docs/authoring-tools.md for the full guide.
"""

from typing import Optional
from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from .impl import do_the_thing


class ExampleParams(BaseModel):
    target: str = Field(..., description="What to operate on. Be specific in this docstring; the model reads it.")
    option: Optional[str] = Field(None, description="An optional flag. Document allowed values here.")


@tool(
    name="example.do_thing",          # <domain>.<verb>
    card="cards/do_thing.md",         # path relative to this file
    schema=ExampleParams,
    classification="internal",        # public | internal | confidential | restricted
    owner="team-replace-me",
    tags=["example", "replace-me"],
)
def do_thing(params: ExampleParams, ctx: ToolCtx) -> ToolResult:
    return do_the_thing(params, ctx)
