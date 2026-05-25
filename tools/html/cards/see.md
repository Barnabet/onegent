---
tool: html.see
version: 1
owner: team-doc-ai
classification: [internal]
tags: [html, read, vision]
---

# html.see

## Purpose
Rasterise up to 5 pages of an HTML file and inject them into the
conversation as images, so the model can *look* at the report rather
than only parse its text. Mirrors `pdf.see` / `pptx.see` for HTML files:
under the hood the file is converted to PDF once (`soffice --convert-to
pdf`), then the selected pages are rendered with `pypdfium2`.

The page numbers refer to the **print pagination** of the document
(the same paginator that `@media print` uses). For reports authored
with `html.create`, that gives stable per-page screenshots that match
what the user would see in a printed copy.

## When to use
- Verifying your own output after `html.create`. **Always do this once
  and look for layout issues (see the html_reporting skill QA checklist).**
- The user asks "show me what page 2 looks like" or "is this readable?".
- You suspect the HTML mis-renders (overflowing tables, broken charts).

## When NOT to use
- For the readable text — `html.extract_text` is far cheaper.
- To process many pages at once — this tool refuses more than 5 pages
  per call (`too_many_pages`).

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.html` / `.htm` file. |
| pages | string | no | 1-based page spec; max 5, e.g. `"1"`, `"2-4"`, `"1,3,5"`. Omit to render page 1 only. |
| scale | float | no | Render scale; `2.0` ≈ 200dpi. Keep ≤ `3.0`. Default `2.0`. |
| timeout_seconds | int | no | LibreOffice subprocess hard limit (default 120). |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved>",
    page_count: <int>,                     // total pages in the printed pagination
    rendered: [{ page: <1-based>, bytes: <b64 length> }, ...],
    scale: <float>
  },
  images: [ToolImage, ...]                  // attached to the next turn as multimodal content
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdfium2` is not installed, or `soffice` is not on `PATH`.
- `page_out_of_range` / `invalid_input` — bad `pages` spec.
- `too_many_pages` — more than 5 pages requested in a single call.
- `timeout` / `convert_failed` — LibreOffice failed.
- `render_failed` — `pypdfium2` raised on a specific page.

## Examples
### See page 1 (the default)
Call: `html.see(path="/tmp/report.html")`

### See pages 2-4
Call: `html.see(path="/tmp/report.html", pages="2-4")`

### See three scattered pages
Call: `html.see(path="/tmp/long.html", pages="1,3,5")`

## See also
- `html.create` — author the HTML in the first place.
- `html.extract_text` — cheap text-only inspection.
- `html.to_pdf` — keep the PDF instead of just page images.
