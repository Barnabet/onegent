---
tool: pdf.rotate
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, transform]
---

# pdf.rotate

## Purpose
Rotate one or more pages of a PDF by a multiple of 90 degrees and write the
result to a new file.

## When to use
- A scanned PDF arrived with pages sideways or upside-down.
- The user explicitly asks to rotate page N by 90/180/270 degrees.

## When NOT to use
- To resize or crop pages — rotation only changes orientation, not geometry.
- To rotate an image embedded in the PDF — that's an image-editing task; this
  tool rotates whole pages.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pdf`. |
| pages | string | no | 1-based page spec to rotate. Omit to rotate every page. |
| degrees | int | yes | One of `90`, `180`, `270`, `-90`, `-180`, `-270`. |
| output | string | yes | Destination `.pdf` path. |
| overwrite | bool | no | Replace existing destination. Default false. |

## Returns
On success: `{ok: true, data: {output, rotated_pages: [int, ...], degrees}}`

## Errors
- `file_not_found` / `unsupported_format` — bad input file.
- `invalid_input` — `degrees` not in the allowed set, or `pages` spec malformed.
- `page_out_of_range` — `pages` references pages that don't exist.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Rotate the whole document 90° clockwise
Call: `pdf.rotate(path="/tmp/scan.pdf", degrees=90, output="/tmp/scan-up.pdf")`

### Rotate just page 3
Call: `pdf.rotate(path="/tmp/scan.pdf", pages="3", degrees=180, output="/tmp/scan-fix.pdf")`

## See also
- `pdf.split` — extract a subset of pages.
- `pdf.see` — confirm orientation visually.
