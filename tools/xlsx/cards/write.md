---
tool: xlsx.write
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, create]
---

# xlsx.write

## Purpose
Create a brand-new spreadsheet from in-memory rows. Supports `.xlsx`/`.xlsm`
(single- or multi-sheet) and `.csv`/`.tsv` (single-sheet only). Never
modifies an existing workbook in place — see `xlsx.edit_cells` for that.

## When to use
- The user asks you to produce a fresh spreadsheet from data you have already
  computed or extracted.
- A skill needs to materialise a multi-sheet workbook (e.g. one sheet per
  region) in one call.

## When NOT to use
- To edit specific cells of an existing workbook (preserving everything else)
  — use `xlsx.edit_cells`.
- To restyle existing cells — use `xlsx.format`.
- To convert between formats — use `xlsx.convert`.
- To write computed values from formulas — write the formula via
  `xlsx.edit_cells` (or as a string here) and then run `xlsx.recalc`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| output | string | yes | Destination path. Extension picks the format. |
| overwrite | bool | no | Replace existing file. Default false. |
| sheets | object | no* | Multi-sheet form: `{sheet_name: {headers?, rows}}`. xlsx only. |
| sheet_name | string | no* | Single-sheet form: name of the sheet (default 'Sheet1'). |
| headers | list | no* | Single-sheet form: header row. |
| rows | list[list] | no* | Single-sheet form: data rows. |

\* Provide either `sheets` (multi-sheet) **or** `sheet_name`/`headers`/`rows`
(single-sheet). Mixing both is undefined.

### Formula cells
A string value beginning with `=` (e.g. `"=SUM(A2:A10)"`) is written as an
Excel formula. The cell's *value* is not materialised until you run
`xlsx.recalc`. CSV/TSV outputs treat such strings literally.

## Returns
```
{ok: true, data: {output, sheet_names: [...], sheet_count: <int>}}
```

## Errors
- `invalid_input` — neither `sheets` nor `headers`/`rows` was provided; or a
  malformed sheet spec; or CSV requested with multiple sheets.
- `unsupported_format` — output extension is not tabular.
- `output_exists` — file exists and `overwrite=false`.
- `write_failed` — disk or library error while saving.
- `dependency_missing` — openpyxl is not installed (xlsx output).

## Examples
### Single-sheet xlsx
Call:
```
xlsx.write(
  output="/tmp/loans.xlsx",
  sheet_name="Loans",
  headers=["id", "amount"],
  rows=[["L1", 100], ["L2", 250]]
)
```

### Multi-sheet workbook
Call:
```
xlsx.write(
  output="/tmp/quarterly.xlsx",
  sheets={
    "Q1": {"headers": ["region","net"], "rows": [["EMEA", 12], ["NA", 18]]},
    "Q2": {"headers": ["region","net"], "rows": [["EMEA", 14], ["NA", 22]]}
  }
)
```

### CSV output
Call: `xlsx.write(output="/tmp/loans.csv", headers=["id","amount"], rows=[["L1",100]])`

### A sheet with totals as formulas (then recalc)
1. `xlsx.write(output="/tmp/m.xlsx", sheet_name="M", headers=["amt"], rows=[[10],[20],[30],["=SUM(A2:A4)"]])`
2. `xlsx.recalc(path="/tmp/m.xlsx")`

## See also
- `xlsx.edit_cells` — modify cells in an existing workbook.
- `xlsx.format` — apply font / fill / number format after writing.
- `xlsx.recalc` — materialise formula results.
- `xlsx.convert` — same data shape, different format.
