---
tool: xlsx.info
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, metadata]
---

# xlsx.info

## Purpose
Return the sheet inventory of a spreadsheet (name, shape, header preview)
plus workbook metadata, without dumping the actual rows.

## When to use
- The user gives you a workbook and you need to decide *which* sheet(s)
  matter before doing anything else — especially for multi-sheet `.xlsx`
  files.
- A skill needs the column names of every sheet to pick the right one or
  to compose an `xlsx.sql` query.
- The user asks "what's in this file?" — answer with the inventory before
  optionally drilling in.

## When NOT to use
- To read the actual data — use `xlsx.read` (raw rows) or `xlsx.sql`
  (computation).
- To inspect a PDF — use `pdf.read`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.xlsx`, `.xlsm`, `.csv`, or `.tsv` file. |

## Returns
```
{ok: true, data: {
  format: "xlsx" | "xlsm" | "csv" | "tsv",
  sheet_count: <int>,
  sheets: [
    {name, row_count, col_count, headers_preview: [...]},
    ...
  ],
  metadata: {title, creator, created, modified}   # xlsx/xlsm only
}}
```
`row_count` excludes the header row.

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — extension not in `.xlsx`, `.xlsm`, `.csv`, `.tsv`.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Inventory a multi-sheet workbook
Call: `xlsx.info(path="/data/q3-report.xlsx")`
Returns: `{ok: true, data: {sheet_count: 3, sheets: [{name: "Revenue", row_count: 120, col_count: 8, headers_preview: [...]}, ...]}}`

### Shape of a CSV
Call: `xlsx.info(path="/data/loans.csv")`

## See also
- `xlsx.read` — once you know which sheet you want.
- `xlsx.sql` — to compute over the sheets you discovered here.
