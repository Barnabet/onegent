---
tool: repo.scaffold_tool
version: 1
owner: team-platform-ai
classification: [internal]
tags: [scaffold, write, tool-authoring]
---

# repo.scaffold_tool

## Purpose
Create the skeleton files for a new tool from the canonical template:
`registry.py`, `impl.py`, `cards/<verb>.md`, and a stub test file.

## When to use
- The skill_creator skill has confirmed (via `repo.search_catalog`) that the
  proposed tool does not duplicate an existing one, and the user has agreed
  on the name and owner.

## When NOT to use
- Before running a dedup check — always call `repo.search_catalog` first.
- To modify an existing tool — this tool only creates new artifacts and
  refuses overwrites.
- To create a tool in a domain you have not discussed with the user — the
  domain (`<domain>` in `<domain>.<verb>`) is a long-lived shared namespace
  and shouldn't be invented on the fly.

## Parameters
| name | type | required | description |
|---|---|---|---|
| name | string | yes | Full tool name as `<domain>.<verb>`, lowercase + underscores only. |
| owner | string | yes | Owning team, e.g. `"team-credit-ai"`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    tool: "<name>",
    created: ["tools/<domain>/", "tools/<domain>/cards/<verb>.md", ...],
    next_steps: [...]   # human-readable list of follow-ups
  }
}
```

## Errors
- `invalid_name` — name not `<domain>.<verb>` or contains invalid characters.
- `already_exists` — tool with that name is already registered, or the card
  file already exists.

## Examples
### First tool in a new domain
Call: `repo.scaffold_tool(name="email.send", owner="team-comms-ai")`
Returns: `{ok: true, data: {tool: "email.send", created: ["tools/email"], next_steps: [...]}}`

### Adding a new verb to an existing domain
Call: `repo.scaffold_tool(name="xlsx.add_chart", owner="team-doc-ai")`
Returns: `{ok: true, data: {tool: "xlsx.add_chart", created: ["tools/xlsx/cards/add_chart.md"], next_steps: [...]}}`

## See also
- `repo.search_catalog` — call first to confirm no duplicate.
- `repo.scaffold_skill` — for new skills.
