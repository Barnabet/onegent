---
tool: xlsx.convert
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, convert]
---

# xlsx.convert

## Purpose
Convert a tabular file between `.xlsx`/`.xlsm`/`.csv`/`.tsv`, optionally
extracting one sheet from a multi-sheet workbook or exploding every sheet
into its own CSV.

## When to use
- The user wants a workbook as CSV (for a downstream tool, a diff, an email).
- The user wants a CSV/TSV imported into a workbook.
- The user wants every sheet of a multi-sheet workbook as separate CSVs
  (one-file-per-sheet) — pass `explode_sheets=true`.
- The user wants to extract a single sheet of a workbook into its own
  smaller workbook.

## When NOT to use
- To change cell values — use `xlsx.edit_cells`.
- To restyle — use `xlsx.format`.
- To read the rows — use `xlsx.read` or `xlsx.sql`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Source file (`.xlsx`/`.xlsm`/`.csv`/`.tsv`). |
| output | string | yes | Destination file, or destination directory when `explode_sheets=true`. Extension picks the target format. |
| overwrite | bool | no | Replace existing output(s). Default false. |
| sheet | string | no | For xlsx → csv/tsv or xlsx → xlsx single-sheet extract: which sheet to take. Default: first. |
| explode_sheets | bool | no | If true and source is multi-sheet xlsx, write one CSV per sheet into the directory `output`. |

## Returns
Single-file conversion:
```
{ok: true, data: {output, sheet, sheet_count: 1}}
```
Explode mode:
```
{ok: true, data: {output_dir, files: [...], sheet_count: <int>}}
```

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source or output extension is not tabular.
- `sheet_not_found` — `sheet` is not in the workbook.
- `output_exists` — destination exists and `overwrite=false`.
- `invalid_input` — bad combination of `output` extension and mode.
- `dependency_missing` — openpyxl is not installed and xlsx is involved.

## Examples
### Workbook (first sheet) → CSV
Call: `xlsx.convert(path="/data/report.xlsx", output="/data/report.csv")`

### Workbook → CSV, pick the sheet
Call: `xlsx.convert(path="/data/report.xlsx", sheet="Revenue", output="/data/revenue.csv")`

### CSV → xlsx
Call: `xlsx.convert(path="/data/loans.csv", output="/data/loans.xlsx")`

### TSV → CSV
Call: `xlsx.convert(path="/data/x.tsv", output="/data/x.csv")`

### Explode every sheet into its own CSV
Call: `xlsx.convert(path="/data/report.xlsx", output="/data/report-sheets/", explode_sheets=true)`

### Extract a single sheet into a one-sheet workbook
Call: `xlsx.convert(path="/data/report.xlsx", sheet="Revenue", output="/data/revenue.xlsx")`

## See also
- `xlsx.read` — once converted, to inspect the result.
- `xlsx.write` — to assemble multi-sheet workbooks from scratch.
