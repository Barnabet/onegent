---
tool: repo.read_catalog
version: 1
owner: team-platform-ai
classification: [public]
tags: [catalog, read, reference]
---

# repo.read_catalog

## Purpose
Return the live catalog of every registered tool and discovered skill as
structured data: names, owners, classifications, tags, and purpose lines.

## When to use
- A skill needs to know what tools exist (e.g. the skill_creator before
  proposing a new tool).
- You need a quick inventory before deciding what to build.

## When NOT to use
- When you want to find tools matching a specific need — use
  `repo.search_catalog`, which scores by relevance.
- When you want the raw markdown of a tool card — read the card directly via
  the catalog entry's tool name + your knowledge of the layout, or browse
  `docs/tool-catalog.md` rendered output.

## Parameters
_(none)_

## Returns
On success:
```
{
  ok: true,
  data: {
    tools: [
      {name, version, owner, classification, tags, domain, purpose},
      ...
    ],
    skills: [
      {name, version, description},
      ...
    ]
  }
}
```

## Errors
_(none — the tool always succeeds with the current state.)_

## Examples
### Inventory before scaffolding
Call: `repo.read_catalog()`
Returns: `{ok: true, data: {tools: [...], skills: [...]}}`

## See also
- `repo.search_catalog` — relevance-scored lookup, preferred for dedup checks.
- `repo.read_doc` — read raw markdown from `docs/`.
