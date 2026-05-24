---
tool: xlsx.read
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, tabular]
---

# xlsx.read

## Purpose
Read a spreadsheet file (`.xlsx`, `.xlsm`, `.csv`, or `.tsv`) and return its
contents as a header row + list of data rows.

## When to use
- The user gives you a path to a spreadsheet and asks you to inspect, analyse,
  or summarise its contents.
- A skill needs the rows from a workbook before doing any analysis on them.

## When NOT to use
- For writing or modifying a workbook — not supported yet; will be `xlsx.write_*`.
- For complex pivot / chart inspection — not supported; returns raw cell values.
- For reading PDFs of spreadsheet exports — use `pdf.extract_tables` (when
  available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Absolute or relative path to the file. |
| sheet | string | no | Sheet name (xlsx only). Defaults to the first sheet. |
| has_header | bool | no | If true (default), the first row becomes `headers`; otherwise it stays in `rows`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    sheet: "<name>",
    headers: ["col1", "col2", ...] | null,
    rows: [[v1, v2, ...], ...],
    row_count: <int>
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — extension not in `.xlsx`, `.xlsm`, `.csv`, `.tsv`.
- `sheet_not_found` — requested sheet name is not in the workbook.
- `dependency_missing` — openpyxl is not installed in this environment.

## Examples
### Read default sheet of an xlsx
Call: `xlsx.read(path="/data/loans.xlsx")`
Returns: `{ok: true, data: {sheet: "Sheet1", headers: ["id","amount"], rows: [["L1",100], ...], row_count: 20}}`

### Read a specific sheet
Call: `xlsx.read(path="/data/loans.xlsx", sheet="Q1")`

### Read a CSV
Call: `xlsx.read(path="/data/loans.csv")`

## See also
- `text.extract_lines` — for prose, not tabular sources.
- `docstore.fetch` — when the source is internally stored rather than at a path.
