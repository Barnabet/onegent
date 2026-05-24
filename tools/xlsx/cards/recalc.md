---
tool: xlsx.recalc
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, formula, recalc]
---

# xlsx.recalc

## Purpose
Recalculate every formula in an `.xlsx`/`.xlsm` workbook (via LibreOffice
headless), materialise the resulting values, and report any residual Excel
errors (`#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, `#NAME?`, `#NUM!`, `#NULL!`).

Required after any `xlsx.write` / `xlsx.edit_cells` call that injected
formulas — openpyxl writes formula strings but does not evaluate them.

## When to use
- You injected `=SUM(...)`, `=AVERAGE(...)`, `=VLOOKUP(...)` etc. via
  `xlsx.write` or `xlsx.edit_cells` and the user needs the *values* visible
  in the workbook (e.g. so a downstream tool that reads with `data_only=true`
  sees them).
- You want a post-edit error scan to catch broken references before
  delivering the file.

## When NOT to use
- Workbooks with no formulas (CSV outputs, value-only tables) — nothing to
  recalculate.
- Performance-sensitive loops — LibreOffice startup is non-trivial.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Workbook to recalculate. |
| output | string | no | Where to write the result. Omit to overwrite the input in place. |
| overwrite | bool | no | If `output` is given and exists, allow replacing it. |
| timeout_seconds | int | no | Hard timeout for the LibreOffice call (default 60). |

## Returns
```
{ok: true, data: {
  output: "<path>",
  status: "success" | "errors_found",
  total_errors: <int>,
  error_summary: {
    "#REF!": {"count": 2, "locations": ["Sheet1!B5", "Sheet1!C10"]},
    ...
  }
}}
```

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source is not `.xlsx`/`.xlsm`.
- `dependency_missing` — `soffice` (LibreOffice) is not on PATH.
- `recalc_failed` — LibreOffice exited non-zero or produced no output.
- `timeout` (retriable) — LibreOffice did not finish in time.
- `output_exists` — `output` exists and `overwrite=false`.

## Examples
### Recalculate in place
Call: `xlsx.recalc(path="/data/model.xlsx")`

### Recalculate to a separate file
Call: `xlsx.recalc(path="/data/model.xlsx", output="/data/model-final.xlsx")`

### Typical edit → recalc → verify chain
1. `xlsx.edit_cells(path="...", output="m2.xlsx", cells=[{"cell":"B11","value":"=SUM(B2:B10)"}])`
2. `xlsx.recalc(path="m2.xlsx")`
3. If `status="errors_found"`, inspect `error_summary` and fix the formulas
   with another `xlsx.edit_cells` round.

## See also
- `xlsx.write`, `xlsx.edit_cells` — produce the formulas this recalculates.
- `xlsx.read` — read the values back after recalc.
