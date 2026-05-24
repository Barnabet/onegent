# Authoring tools

A **tool** is a Python function the agent can call. A tool has three artifacts:

1. **Implementation** — the Python function (`impl.py`).
2. **Registration** — the `@tool` decorator binding name, schema, classification, owner (`registry.py`).
3. **Tool card** — the markdown doc the model reads to decide when and how to call it (`cards/<tool>.md`).

All three are required. A tool without a card is not a tool.

## The golden rules

1. **One tool, one verb, one domain.** `xlsx.read`, not `xlsx.read_and_summarize`.
2. **Tools live in `tools/<domain>/`, never in `tools/<skill_name>/`.** They are shared.
3. **Check the catalog before writing.** Run `python scripts/new_tool.py <name>` — it greps for collisions and asks you to justify.
4. **Tools are stateless.** No globals, no in-memory caches across calls. Pass everything in via params.
5. **Tools never raise to the model.** They return a `ToolResult` envelope. Crashes are bugs, not signaling.
6. **Tools never shell out, never install, never touch the model.** A tool that needs an LLM call is a *skill*, not a tool.
7. **Version your contracts.** Breaking changes ship as `<tool>_v2`, with the old one still around for one release.

## The return envelope

Every tool returns the same shape. Skills and the framework rely on it.

```python
class ToolResult(BaseModel):
    ok: bool
    data: Optional[dict] = None        # present when ok=True
    error: Optional[ToolError] = None  # present when ok=False
    warnings: list[str] = []
    citations: list[Citation] = []     # source refs when applicable
```

```python
class ToolError(BaseModel):
    code: str          # snake_case, stable, enumerated in the card
    message: str       # human-readable, safe to surface to the user
    retriable: bool    # can the agent retry as-is?
```

Error `code` values are part of the contract. Adding one is a minor version bump. Changing one is a breaking change → new tool name.

## File layout

```
tools/<domain>/
├── __init__.py
├── registry.py         # @tool registrations, one per public function
├── impl.py             # the actual Python (or split into impl/*.py)
├── cards/
│   ├── <tool_a>.md     # one card per registered tool
│   └── <tool_b>.md
└── tests/
    ├── test_<tool_a>.py
    └── fixtures/
```

## Writing the implementation

```python
# tools/xlsx/impl.py
from pydantic import BaseModel
from runtime.tool_registry import tool, ToolCtx, ToolResult

class ReadParams(BaseModel):
    path: str
    sheet: Optional[str] = None
    range: Optional[str] = None

@tool(
    name="xlsx.read",
    card="cards/read.md",
    schema=ReadParams,
    classification="internal",
    owner="team-doc-ai",
    tags=["spreadsheet", "read", "tabular"],
)
def read(params: ReadParams, ctx: ToolCtx) -> ToolResult:
    # ... do the work ...
    return ToolResult(ok=True, data={"sheet": ..., "rows": ..., "headers": ...})
```

- `params` is a pydantic model. Its JSON schema becomes the tool's `parameters` in the LLM tool-call spec. **Do not** accept `**kwargs`.
- `ctx` carries `run_id`, the user identity, the audit logger, and the classification ceiling. Use it for logging, never bypass it.
- The function must be import-safe. No network calls at import time. No global side effects.

## Writing the tool card

The card is **the doc the LLM reads** to decide whether and how to call the tool. It is *not* internal developer documentation — it is prompt context. Write for the model.

### Template

```markdown
---
tool: <domain>.<name>
version: 1
owner: <team-name>
classification: [internal]
tags: [<tag1>, <tag2>]
---

# <domain>.<name>

## Purpose
One sentence. What it does, not how.

## When to use
- Specific trigger situations, in the model's voice.
- e.g. "The user gives you a .xlsx path and asks to inspect its contents."

## When NOT to use
- Near-miss situations that should go elsewhere — link the alternative.
- e.g. "For .csv files, use `csv.read` — it's faster and has no LibreOffice dependency."
- e.g. "If the user wants pandas-shaped output, use `xlsx.to_dataframe`."

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Absolute path to .xlsx or .xlsm |
| sheet | string | no | Sheet name; defaults to the active sheet |
| range | string | no | A1 notation, e.g. "A1:D20" |

## Returns
On success:
`{ok: true, data: {sheet, headers: [...], rows: [[...]]}}`

## Errors
- `file_not_found` — the path does not exist on disk.
- `unsupported_format` — file is not a valid Excel workbook.
- `sheet_not_found` — the requested sheet name is not in the workbook.

## Examples
### Read whole active sheet
Call: `xlsx.read(path="/data/loans.xlsx")`
Returns: `{ok: true, data: {sheet: "Sheet1", headers: ["id","amount"], rows: [["L1", 100], ...]}}`

### Read a range from a named sheet
Call: `xlsx.read(path="/data/loans.xlsx", sheet="Q1", range="A1:F50")`

## See also
- `xlsx.to_dataframe` — same input, pandas-shaped output.
- `csv.read` — for CSV files.
- `xlsx.write_cells` — to modify a workbook.
```

### What makes a great card

- **"When NOT to use" with cross-links is the single most important section.** If you cannot name at least one neighboring tool the reader might confuse yours with, your tool is either too generic or duplicates something that exists. Review will reject it.
- **Examples are concrete calls + concrete returns.** No abstract "you might want to do X." The model copies patterns.
- **Errors are enumerated.** The model will surface them; vague errors produce vague user-facing messages.
- **Parameter descriptions explain semantics, not types.** The schema already says it's a string. Tell the model *what kind* of string ("A1 notation").

### Good vs bad — one example

**Bad**

```markdown
# xlsx.read
Reads an excel file. Takes a path and returns the data.

## Parameters
- path: the file path
```

This card will produce wrong tool calls. The model doesn't know which file formats are accepted, what "the data" looks like, what fails when, or which other tool to use instead.

**Good** — the template above. The model can call it correctly on the first try, knows when to pick `csv.read` instead, and knows what `file_not_found` means.

## Classification and ownership

The frontmatter fields `classification`, `owner`, and `tags` are not cosmetic.

- **`classification`** gates which packs can bind the tool. A pack with ceiling `internal` cannot bind a `confidential` tool. The framework refuses.
- **`owner`** is the team paged when the tool breaks. PR review requires the owner team to approve changes to their tools.
- **`tags`** drive the catalog's "find by capability" index. Skill authors search by tag.

## Versioning

- Adding an optional parameter, an error code, or a returned field → minor bump (`version: 2`), card updated, no rename.
- Removing/renaming a parameter, changing return shape, removing an error code → **new tool name** (`xlsx.read_v2`). Old tool stays for one release with a `## Deprecated` callout in its card pointing to the successor.
- Skills migrate to the new tool via PRs in their own repos; old tool is dropped only after all skills moved.

## Testing

Every tool ships with tests in `tools/<domain>/tests/`. Three categories, all required:

1. **Happy path** — at least one test per documented example in the card.
2. **Each error code** — one test per `## Errors` entry.
3. **Schema round-trip** — pydantic accepts a valid `params` and rejects an invalid one.

CI also runs a **card lint**: every tool registered in `registry.py` must have a card whose frontmatter `tool:` matches, with all required sections present.

## Checklist before opening a PR

- [ ] Ran `python scripts/new_tool.py <name>` and resolved any catalog collisions.
- [ ] Implementation is stateless and import-safe.
- [ ] Returns `ToolResult` envelope; never raises to the caller.
- [ ] Pydantic schema models `params` exactly.
- [ ] Card present, follows the template, has a non-empty **When NOT to use**.
- [ ] Card frontmatter has `owner`, `classification`, `tags`.
- [ ] Tests cover every example and every error code.
- [ ] `python scripts/check_catalog.py` is green.
