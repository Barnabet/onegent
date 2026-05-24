---
tool: pdf.extract_text
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, text]
---

# pdf.extract_text

## Purpose
Extract the textual content of a PDF, page by page. Uses `pdfplumber` when
available (layout-aware), falls back to `pypdf` otherwise.

## When to use
- The user wants the prose / written content of a PDF.
- A skill needs the text body to summarise, search, or feed downstream.
- You can scope to a page range with `pages` to keep the response small.

## When NOT to use
- For tables — use `pdf.extract_tables`; running `extract_text` on a table
  produces a column-jumbled mess.
- For scanned PDFs that have no embedded text layer — use `pdf.ocr`. A first
  hint: `extract_text` returns empty strings or whitespace only.
- To *look* at the page (e.g. understand a chart) — use `pdf.see`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pdf` file. |
| pages | string | no | 1-based page spec, e.g. `"1"`, `"1-3"`, `"1,3-5,8"`. Omit to use the document's first `max_pages` pages. |
| preserve_layout | bool | no | If true and pdfplumber is available, preserves columns/whitespace. Default false. |
| max_pages | int | no | Cap on the number of pages returned (default 5). Applied after the `pages` spec, so asking for `"1-50"` still gives you only the first 5 unless you raise this. When the cap drops pages, the payload includes `truncated: true` and `skipped_pages: [...]`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    backend: "pdfplumber" | "pypdf",
    page_count: <int>,
    char_count: <int>,
    pages: [{page: <1-based>, text: "..."}, ...],
    // present only when truncated:
    requested_page_count: <int>,
    returned_page_count: <int>,
    skipped_pages: [<1-based>, ...],
    truncated: true,
    truncation_note: "Returned N of M requested pages..."
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file is not a readable PDF.
- `page_out_of_range` — `pages` spec references pages outside `1..page_count`.
- `invalid_input` — `pages` spec is malformed.
- `extraction_failed` — the backend raised while parsing the PDF.

## Examples
### Extract everything
Call: `pdf.extract_text(path="/tmp/report.pdf")`

### Extract pages 1 to 3 only
Call: `pdf.extract_text(path="/tmp/report.pdf", pages="1-3")`

### Extract with column layout preserved
Call: `pdf.extract_text(path="/tmp/two-col.pdf", preserve_layout=true)`

## See also
- `pdf.extract_tables` — for structured tabular content.
- `pdf.ocr` — for scanned PDFs with no text layer.
- `pdf.see` — render pages as images to read visual content.
