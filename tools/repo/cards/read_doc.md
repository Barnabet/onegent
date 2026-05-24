---
tool: repo.read_doc
version: 1
owner: team-platform-ai
classification: [public]
tags: [docs, read, reference]
---

# repo.read_doc

## Purpose
Read a markdown file from the repository's `docs/` directory and return its
full contents.

## When to use
- A skill needs to consult the authoring guides at runtime (e.g. the
  skill_creator reads `authoring-tools.md` before guiding the user).
- The user asks "what does the authoring guide say about X" and the answer
  lives in `docs/`.

## When NOT to use
- For reading anything outside `docs/` — this tool refuses out-of-tree paths.
- For reading a skill's `references/*.md` — use `repo.read_doc` only against
  the top-level `docs/` directory; references are loaded by the framework
  itself when a skill activates.
- For reading the live tool/skill catalog data — use `repo.read_catalog`,
  which returns structured JSON, not raw markdown.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path relative to `docs/`, e.g. `"authoring-tools.md"` or `"example-kyc-screening.md"`. |

## Returns
On success: `{ok: true, data: {path: "docs/...", content: "<full markdown>"}}`

## Errors
- `path_outside_docs` — path attempts to escape `docs/`.
- `not_found` — no such file under `docs/`.

## Examples
### Read the tool-authoring guide
Call: `repo.read_doc(path="authoring-tools.md")`
Returns: `{ok: true, data: {path: "docs/authoring-tools.md", content: "# Authoring tools\n..."}}`

### Read the worked example
Call: `repo.read_doc(path="example-kyc-screening.md")`

## See also
- `repo.read_catalog` — structured tool/skill list, not raw markdown.
- `repo.search_catalog` — find tools by name/tag/description.
