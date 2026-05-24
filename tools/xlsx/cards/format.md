---
tool: xlsx.format
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, format, style]
---

# xlsx.format

## Purpose
Apply font, fill, alignment, number format, and column widths to a range in
an existing `.xlsx`/`.xlsm` workbook. Cell values are preserved.

## When to use
- The user asks for a header row to be bold, a column to be currency-formatted,
  zero values shown as a dash, a key assumption cell highlighted yellow, or a
  column widened.
- A skill is producing a deliverable and needs the financial-model conventions
  applied (blue inputs, black formulas, $#,##0 currency, etc.).

## When NOT to use
- To change cell *values* — use `xlsx.edit_cells`.
- To build a new workbook — use `xlsx.write`, then come back here.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Source `.xlsx`/`.xlsm`. |
| output | string | yes | Destination `.xlsx`/`.xlsm`. |
| overwrite | bool | no | Replace existing output. Default false. |
| sheet | string | no | Target sheet; defaults to the first. |
| range | string | yes | A1 range, e.g. `'A1'`, `'A1:C10'`, `'B:B'`, `'2:2'`. |
| font_name | string | no | e.g. `'Arial'`. |
| font_size | number | no | Points. |
| bold | bool | no | |
| italic | bool | no | |
| font_color | string | no | ARGB/RGB hex, e.g. `'0000FF'` (industry-standard blue for hardcoded inputs). |
| fill_color | string | no | ARGB/RGB hex, e.g. `'FFFF00'` for a yellow assumption highlight. |
| align | string | no | `'left'` \| `'center'` \| `'right'`. |
| number_format | string | no | Excel number format, e.g. `'$#,##0;($#,##0);-'`, `'0.0%'`, `'0.0x'`. |
| column_widths | object | no | `{column_letter: width}` map applied to the same sheet. |

### Financial-model colour conventions (recommended)
- Hardcoded inputs / scenario knobs: blue text `'0000FF'`.
- Formulas / calculations: black text (default).
- Cross-sheet links: green text `'008000'`.
- External-file links: red text `'FF0000'`.
- Key assumption cells: yellow fill `'FFFF00'`.

## Returns
```
{ok: true, data: {output, sheet, cells_formatted: <int>}}
```

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source is not `.xlsx`/`.xlsm`.
- `sheet_not_found` — `sheet` is not in the workbook.
- `output_exists` — destination exists and `overwrite=false`.
- `invalid_input` — missing or bad `range`.
- `write_failed` — disk or library error while saving.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Bold the header row and widen columns
Call:
```
xlsx.format(
  path="/data/m.xlsx", output="/data/m-styled.xlsx",
  range="A1:D1", bold=true, fill_color="DDDDDD",
  column_widths={"A": 20, "B": 14, "C": 14, "D": 14}
)
```

### Currency format on a column, zeros as dash
Call:
```
xlsx.format(
  path="/data/m.xlsx", output="/data/m2.xlsx",
  range="C2:C100", number_format="$#,##0;($#,##0);-"
)
```

### Highlight a key assumption
Call:
```
xlsx.format(
  path="/data/m.xlsx", output="/data/m2.xlsx",
  sheet="Assumptions", range="B2", fill_color="FFFF00", font_color="0000FF", bold=true
)
```

## See also
- `xlsx.edit_cells` — to change values, not styling.
- `xlsx.write` — initial workbook creation.
