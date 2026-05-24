---
tool: pdf.see
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, vision]
---

# pdf.see

## Purpose
Rasterise up to 5 pages of a PDF and inject them into the conversation as
images, so the model can *look* at the page rather than only parse its text.

## When to use
- The user asks about a chart, figure, diagram, signature, stamp, or layout
  feature that text extraction cannot recover.
- `pdf.extract_text` returned empty / nonsensical content and you suspect a
  scan — use `pdf.see` to confirm visually before reaching for `pdf.ocr`.
- The user wants you to compare two pages side by side and judge visual
  similarity.

## When NOT to use
- For the plain text body — `pdf.extract_text` is faster and feeds richer
  content per token.
- For tables that have an embedded text layer — `pdf.extract_tables` returns
  the cells directly. `pdf.see` is for the visual content only.
- To process many pages at once — this tool refuses more than 5 pages per
  call (`too_many_pages`). Call it twice if you must, but consider whether
  the user really needs all of them.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pdf` file. |
| pages | string | no | 1-based page spec; max 5 pages, e.g. `"1"`, `"2-4"`, `"1,3,5"`. Omit to render page 1. |
| scale | float | no | Render scale; `2.0` ≈ 200 dpi. Keep ≤ `3.0` to stay within model image limits. Default `2.0`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved>",
    page_count: <total pages in document>,
    rendered: [{page: <1-based>, bytes: <b64 length>}, ...],
    scale: <float>
  },
  images: [ToolImage, ...]   // attached to the next turn as multimodal content
}
```
The framework automatically appends the images to the next user turn so the
model can see them. The `data` payload itself is the textual summary.

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdfium2` is not installed.
- `page_out_of_range` / `invalid_input` — bad `pages` spec.
- `too_many_pages` — more than 5 pages requested in a single call.
- `render_failed` — the renderer raised on a specific page.

## Examples
### See page 1
Call: `pdf.see(path="/tmp/report.pdf")`

### See pages 2-4 of a deck
Call: `pdf.see(path="/tmp/slides.pdf", pages="2-4")`

### See three scattered pages
Call: `pdf.see(path="/tmp/big.pdf", pages="1,5,12")`

## See also
- `pdf.extract_text` — far cheaper for text content.
- `pdf.ocr` — when you need the text *of* a scanned page, not just to look at it.
- `pdf.read` — to know `page_count` before choosing pages to render.
