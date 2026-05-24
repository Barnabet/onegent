---
tool: repo.search_catalog
version: 1
owner: team-platform-ai
classification: [public]
tags: [catalog, search, dedup]
---

# repo.search_catalog

## Purpose
Search the live tool catalog by free-text query and return ranked hits with
their purpose lines, tags, and owners. Used primarily as a dedup check
before proposing a new tool.

## When to use
- Before scaffolding a new tool, search for near-duplicates the author may
  have missed.
- A skill author is picking tools for a workflow step and wants candidates.

## When NOT to use
- For listing every tool — use `repo.read_catalog`, which returns the full
  inventory without scoring.
- For reading the actual card body of a specific tool — fetch via the
  catalog entry name.

## Parameters
| name | type | required | description |
|---|---|---|---|
| query | string | yes | Free-text, e.g. `"read excel"`, `"summarize text"`, `"docstore"`. Lower-case match. |
| limit | int | no | Max hits returned, default 8, max 50. |

## Returns
On success:
```
{
  ok: true,
  data: {
    query: "<echoed>",
    hits: [
      {name, score, tags, purpose, owner},
      ...   # sorted by score desc
    ]
  }
}
```

## Errors
- `empty_query` — query is empty or whitespace-only.

## Examples
### Dedup check before adding `xlsx.read_sheet`
Call: `repo.search_catalog(query="read excel")`
Returns: `{ok: true, data: {query: "read excel", hits: [{name: "xlsx.read", score: 0.95, ...}, ...]}}`

### Browse summarization tools
Call: `repo.search_catalog(query="summarize", limit=5)`

## See also
- `repo.read_catalog` — full inventory, unranked.
- `repo.scaffold_tool` — call after confirming no duplicate exists.
