---
tool: xlsx.read
version: 2
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, tabular]
---

# xlsx.read

## Purpose
Read a spreadsheet file (`.xlsx`, `.xlsm`, `.csv`, or `.tsv`) and return its
contents as a header row + list of data rows, optionally for every sheet in
a workbook at once.

## When to use
- The user gives you a path to a spreadsheet and wants you to look at the
  actual rows (for a sample, a small dump, or a copy into your reasoning).
- A skill needs the raw cells of a workbook before deciding what to do next.
- The user wants every sheet of a multi-sheet workbook in one call —
  pass `all_sheets=true`.

## When NOT to use
- To *compute* anything (sum, average, group-by, join, filter): call
  `xlsx.sql` instead. Pulling all rows into your context just to sum them is
  wasteful and error-prone.
- To learn shape / sheet names / column previews without the data: call
  `xlsx.info` — much cheaper for large files.
- To modify a workbook: use `xlsx.write`, `xlsx.edit_cells`, `xlsx.format`.
- To read a PDF table: use `pdf.extract_tables`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the file. |
| sheet | string | no | Sheet name (xlsx only). Defaults to the first sheet. Ignored when `all_sheets=true`. |
| has_header | bool | no | If true (default), the first row becomes `headers`; otherwise it stays in `rows`. |
| all_sheets | bool | no | If true, return every sheet of the workbook under `sheets`. Xlsx only. |
| max_rows | int | no | Cap on data rows returned per sheet (default 10). When the sheet has more rows, `rows` is truncated and `truncated: true` is set in the payload. Raise it if you genuinely need more rows; use `xlsx.sql` for aggregations. |

## Returns
Single sheet:
```
{ok: true, data: {
  sheet: "<name>", sheet_names: [...],
  headers: [...] | null, rows: [[...], ...],
  row_count: <int>,            # total data rows in the sheet
  col_count: <int>,
  // present only when truncated:
  returned_row_count: <int>,   # how many rows are actually in `rows`
  truncated: true,
  truncation_note: "Showing first N of M data rows. ..."
}}
```
All sheets (`all_sheets=true`):
```
{ok: true, data: {
  sheet_names: [...],
  sheets: [{sheet, headers, rows, row_count, col_count}, ...]
}}
```
Dates / datetimes are returned as ISO-format strings.

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — extension not in `.xlsx`, `.xlsm`, `.csv`, `.tsv`.
- `sheet_not_found` — requested sheet name is not in the workbook.
- `decode_error` — CSV/TSV file is not UTF-8.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Read default sheet of an xlsx
Call: `xlsx.read(path="/data/loans.xlsx")`

### Read a specific sheet
Call: `xlsx.read(path="/data/loans.xlsx", sheet="Q1")`

### Dump every sheet of a multi-sheet workbook
Call: `xlsx.read(path="/data/report.xlsx", all_sheets=true)`

### Read a CSV without treating the first row as a header
Call: `xlsx.read(path="/data/loans.csv", has_header=false)`

## See also
- `xlsx.info` — sheet inventory + shape, no row data.
- `xlsx.sql` — for anything that needs computation.
- `xlsx.convert` — to reshape between xlsx / csv / tsv.
