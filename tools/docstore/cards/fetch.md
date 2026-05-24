---
tool: docstore.fetch
version: 1
owner: team-platform-ai
classification: [confidential]
tags: [docstore, fetch, read, internal-docs]
---

# docstore.fetch

## Purpose
Retrieve a document from the bank's internal document store by id, entity
name, or short free-text query. Returns the document body plus metadata.

## When to use
- A skill needs to pull a specific internal document — a KYC dossier, a
  credit file, a counterparty profile — to operate on it.
- The user gives you an entity name or an id and asks you to "fetch" or
  "pull up" the dossier.

## When NOT to use
- For searching the open web — use `web.search` (when available).
- For reading repository docs (authoring guides, catalogs) — use
  `repo.read_doc`.
- For reading a local spreadsheet path the user has attached — use
  `xlsx.read` or `text.read_file` (when available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| query | string | yes | An id (e.g. `"globex-kyc-2025"`), an entity name, or a short free-text term. |
| doc_type | string | no | Restrict to a specific type, e.g. `"kyc_dossier"`, `"credit_input"`. |
| latest | bool | no | When multiple match, return the most recently published. Default `true`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    id: "...",
    doc_type: "...",
    entity: "...",
    published: "YYYY-MM-DD",
    body: "<full document text>"
  }
}
```

## Errors
- `store_empty` — the document store is empty (configuration issue).
- `not_found` — no document matched the query.
- `file_missing` — the index references a file that is not on disk.

## Examples
### Fetch a KYC dossier by entity name
Call: `docstore.fetch(query="Globex Corporation", doc_type="kyc_dossier")`
Returns: `{ok: true, data: {id: "globex-kyc-2025", entity: "Globex Corporation SA", ...}}`

### Fetch a credit input file by id
Call: `docstore.fetch(query="acme-credit-input")`

## See also
- `repo.read_doc` — for repository docs, not internal documents.
- `xlsx.read` — when the user has attached an .xlsx file directly.
