---
tool: pdf.split
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, split]
---

# pdf.split

## Purpose
Extract a subset of pages from a PDF into a new file. The selected pages keep
their original order in the destination.

## When to use
- The user wants a specific page range from a larger PDF.
- A skill needs to produce a smaller artefact (e.g. just the executive summary).

## When NOT to use
- To produce one PDF per page — call `pdf.split` once per page with the
  desired `pages` value, or write a thin loop in your skill workflow.
- To concatenate PDFs — use `pdf.merge`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pdf` file. |
| pages | string | yes | 1-based page spec to keep, e.g. `"1-5"` or `"1,3,7-9"`. |
| output | string | yes | Destination `.pdf` path. |
| overwrite | bool | no | If true, replace an existing `output` file. Default false. |

## Returns
On success: `{ok: true, data: {output, page_count, selected_pages: [1,2,...]}}`

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — file is not a readable PDF.
- `page_out_of_range` / `invalid_input` — `pages` spec is bad.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Keep pages 1 through 5
Call: `pdf.split(path="/tmp/big.pdf", pages="1-5", output="/tmp/first5.pdf")`

### Keep a scattered selection
Call: `pdf.split(path="/tmp/big.pdf", pages="1,3,7-9", output="/tmp/sel.pdf")`

## See also
- `pdf.merge` — recombine extracts.
- `pdf.see` — verify what is on a page before splitting.
