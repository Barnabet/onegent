---
tool: xlsx.edit_cells
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, edit, formula]
---

# xlsx.edit_cells

## Purpose
Set the values of specific cells in an existing `.xlsx`/`.xlsm` workbook,
preserving all other cells, sheets, styles, and formulas. Write to a fresh
output path; the input is never modified in place.

## When to use
- The user wants to update a small number of cells in a workbook (assumption
  cells, totals, a status flag) without rebuilding the whole file.
- A skill needs to inject a formula (e.g. `=SUM(B2:B10)`) into an existing
  template.

## When NOT to use
- To rebuild a workbook from scratch — use `xlsx.write`.
- To apply font / fill / number formats — use `xlsx.format`.
- To recompute formula results after editing — chain `xlsx.recalc`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Source `.xlsx`/`.xlsm`. |
| output | string | yes | Destination `.xlsx`/`.xlsm`. |
| overwrite | bool | no | Replace existing output. Default false. |
| sheet | string | no | Target sheet name; defaults to the first sheet. |
| cells | list[{cell, value}] | yes | A1-notation cells and the values to assign. String values that start with `=` are written as Excel formulas. |

## Returns
```
{ok: true, data: {output, sheet, cells_written: <int>}}
```
A `warnings[]` entry will mention `xlsx.recalc` whenever a formula was
written, because openpyxl does not evaluate formulas itself.

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source is not `.xlsx`/`.xlsm`.
- `sheet_not_found` — `sheet` is not in the workbook.
- `output_exists` — destination exists and `overwrite=false`.
- `invalid_input` — empty `cells` list, missing `cell` key, or bad A1 ref.
- `write_failed` — disk or library error while saving.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Update three assumption cells
Call:
```
xlsx.edit_cells(
  path="/data/model.xlsx",
  output="/data/model-v2.xlsx",
  sheet="Assumptions",
  cells=[
    {"cell": "B2", "value": 0.05},
    {"cell": "B3", "value": 0.12},
    {"cell": "B4", "value": "Updated 2025-05"}
  ]
)
```

### Inject a SUM formula then recalc
1. `xlsx.edit_cells(path="/data/m.xlsx", output="/data/m2.xlsx", cells=[{"cell": "B11", "value": "=SUM(B2:B10)"}])`
2. `xlsx.recalc(path="/data/m2.xlsx")`

## See also
- `xlsx.write` — when you're building a brand-new workbook.
- `xlsx.format` — for styling, not values.
- `xlsx.recalc` — materialise formula results.
