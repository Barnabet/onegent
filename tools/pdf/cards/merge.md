---
tool: pdf.merge
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, combine]
---

# pdf.merge

## Purpose
Concatenate two or more PDFs into a single output file, preserving page order.

## When to use
- The user wants to "combine", "merge", or "join" several PDFs into one.
- A skill produced multiple PDFs (e.g. one per section) and needs to deliver
  a single document.

## When NOT to use
- To pick a subset of pages from one PDF — use `pdf.split` instead.
- To overlay a watermark — that's a different operation; merge concatenates,
  it does not stamp.
- To merge a `.docx` and a `.pdf` — first convert the docx via a docx tool,
  then merge.

## Parameters
| name | type | required | description |
|---|---|---|---|
| inputs | string[] | yes | At least 2 paths to existing `.pdf` files, in concat order. |
| output | string | yes | Destination path; must end in `.pdf`. |
| overwrite | bool | no | If true, replace an existing `output` file. Default false. |

## Returns
On success: `{ok: true, data: {output, page_count, source_count}}`

## Errors
- `file_not_found` — one of the `inputs` does not exist.
- `unsupported_format` — one of the `inputs` is not a readable PDF.
- `invalid_input` — fewer than 2 inputs, or `output` doesn't end in `.pdf`.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Merge two PDFs
Call: `pdf.merge(inputs=["/tmp/a.pdf","/tmp/b.pdf"], output="/tmp/ab.pdf")`

### Merge three PDFs, replacing the destination
Call: `pdf.merge(inputs=["/tmp/cover.pdf","/tmp/body.pdf","/tmp/appendix.pdf"], output="/tmp/full.pdf", overwrite=true)`

## See also
- `pdf.split` — extract a page range.
- `pdf.rotate` — fix orientation before merging.
