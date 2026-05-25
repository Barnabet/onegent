---
tool: pptx.see
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, vision]
---

# pptx.see

## Purpose
Rasterise up to 5 slides of a PowerPoint deck and inject them into the
conversation as images, so the model can *look* at the slide rather than
only parse its text. Mirrors `pdf.see` for `.pptx` files: under the hood
the deck is converted to PDF once (`soffice --convert-to pdf`) and the
selected pages are rendered with `pypdfium2`.

## When to use
- The user asks about a chart, diagram, layout, icon, image, or visual
  treatment that text extraction cannot recover.
- `pptx.extract_text` returned nothing useful (the slide is image-heavy)
  and you need to see what's actually on it.
- You want to verify your own newly-authored deck (after `pptx.create`)
  looks right before declaring success. **Always render with `pptx.see`
  at least once after `pptx.create` and look for the issues listed in
  the QA checklist in the PPTX skill.**
- You want to compare two slides side by side.

## When NOT to use
- For the plain text body — `pptx.extract_text` is faster and feeds
  richer content per token.
- For tables that have an embedded text layer in the deck —
  `pptx.extract_text` already gives you cell text. `pptx.see` is for the
  visual content only.
- To process many slides at once — this tool refuses more than 5 slides
  per call (`too_many_slides`). Split the request or pick which 5
  matter most.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |
| slides | string | no | 1-based slide spec; max 5, e.g. `"1"`, `"2-4"`, `"1,3,5"`. Omit to render slide 1 only. |
| scale | float | no | Render scale; `2.0` ≈ 200 dpi. Keep ≤ `3.0` to stay within model image limits. Default `2.0`. |
| timeout_seconds | int | no | Hard limit on the LibreOffice subprocess (default 120). |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved>",
    slide_count: <total slides in deck>,
    rendered: [{ slide: <1-based>, bytes: <b64 length> }, ...],
    scale: <float>
  },
  images: [ToolImage, ...]   // attached to the next turn as multimodal content
}
```
The framework automatically appends the images to the next user turn so
the model can see them. The `data` payload itself is the textual
summary.

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdfium2` is not installed, or
  LibreOffice (`soffice`) is not on `PATH`.
- `slide_out_of_range` / `invalid_input` — bad `slides` spec.
- `too_many_slides` — more than 5 slides requested in a single call.
- `timeout` / `convert_failed` — LibreOffice failed to produce the
  intermediate PDF.
- `render_failed` — `pypdfium2` raised on a specific slide.

## Examples
### See slide 1
Call: `pptx.see(path="/tmp/deck.pptx")`

### See the appendix
Call: `pptx.see(path="/tmp/deck.pptx", slides="14-18")`

### See three scattered slides
Call: `pptx.see(path="/tmp/big-deck.pptx", slides="1,7,12")`

## See also
- `pptx.extract_text` — far cheaper for text content.
- `pptx.convert` — produce the PDF without rendering page images.
- `pptx.read` — to know the slide count before choosing which to render.
