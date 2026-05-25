---
tool: pptx.read
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, metadata]
---

# pptx.read

## Purpose
Open a PowerPoint deck and return its metadata, slide dimensions, and a
per-slide overview (index, title, layout name, shape count, whether the
slide has speaker notes). Use this first whenever you need to know how
big a deck is or what's in it before calling a heavier extraction tool.

## When to use
- The user hands you a `.pptx` path and asks "what is this" / "how many
  slides" / "what's the deck about".
- A skill needs the slide count to drive a `slides=` argument in a
  follow-up call to `pptx.extract_text`, `pptx.split`, or `pptx.see`.
- You want to inventory slide layouts before reusing the deck as a
  template.

## When NOT to use
- For the actual text content — use `pptx.extract_text`.
- For visually inspecting a slide — use `pptx.see` (renders slides as
  images).
- For converting to PDF — use `pptx.convert`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved path>",
    slide_count: <int>,
    slide_width_emu: <int>,
    slide_height_emu: <int>,
    slide_width_in: <float>,
    slide_height_in: <float>,
    metadata: { title, author, subject, keywords, category, comments, last_modified_by },
    slides: [{ index, title, layout, shape_count, has_notes }, ...]
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file does not have a `.pptx` extension or is unreadable.
- `dependency_missing` — `python-pptx` is not installed in this environment.

## Examples
### Inspect a deck
Call: `pptx.read(path="/tmp/quarterly-update.pptx")`
Returns: `{ok: true, data: {slide_count: 18, metadata: {title: "Q4 Update"}, slides: [...]}}`

## See also
- `pptx.extract_text` — actual slide text content.
- `pptx.see` — rasterise slides as images for visual inspection.
- `pptx.convert` — turn the whole deck into a PDF.
