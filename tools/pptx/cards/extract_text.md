---
tool: pptx.extract_text
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, text]
---

# pptx.extract_text

## Purpose
Extract the visible text of every (or a selected subset of) slide in a
PowerPoint deck, plus the speaker notes by default. Walks every shape,
including tables and grouped shapes, joining lines per shape.

## When to use
- The user asks "what does the deck say" / "summarise these slides" /
  "what's on slide 5".
- A skill needs the text of specific slides to do downstream
  summarisation, translation, or comparison.
- You want notes too — they are returned alongside the slide body when
  `include_notes=true` (default).

## When NOT to use
- For visual layout, charts, embedded images, or anything appearance-
  related — use `pptx.see`.
- For speaker notes only — `pptx.extract_notes` returns the same data in
  a leaner shape.
- For converting the deck to PDF or rendering — use `pptx.convert` /
  `pptx.see`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |
| slides | string | no | 1-based slide spec like `"1"`, `"1-3"`, `"1,3-5,8"`. Omit for every slide. |
| include_notes | bool | no | If true (default), also return the speaker notes per slide. |

## Returns
On success:
```
{
  ok: true,
  data: {
    slide_count: <int>,
    char_count: <int>,
    slides: [
      { slide: <1-based>, title: <str|null>, text: <str>, notes: <str> },
      ...
    ]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input file.
- `dependency_missing` — `python-pptx` is not installed.
- `slide_out_of_range` / `invalid_input` — bad `slides` spec.

## Examples
### Whole deck
Call: `pptx.extract_text(path="/tmp/deck.pptx")`

### Slides 1-3 with notes
Call: `pptx.extract_text(path="/tmp/deck.pptx", slides="1-3", include_notes=true)`

### Slide 7 only, no notes
Call: `pptx.extract_text(path="/tmp/deck.pptx", slides="7", include_notes=false)`

## See also
- `pptx.read` — slide count + per-slide metadata first, before extracting.
- `pptx.extract_notes` — notes only.
- `pptx.see` — image renders for visual content.
