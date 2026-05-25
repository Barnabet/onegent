---
tool: pptx.extract_notes
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, notes]
---

# pptx.extract_notes

## Purpose
Return only the speaker notes for every (or selected) slide of a deck.
Equivalent to `pptx.extract_text(include_notes=true)` but without the
visible body text — useful when you want a clean view of the
presenter's narrative.

## When to use
- The user asks for "the speaker notes" / "the script" / "what the
  presenter says".
- You want to compare the on-slide content (already in `extract_text`)
  with the off-slide narrative (`extract_notes`).

## When NOT to use
- When the user wants the full slide content too — use
  `pptx.extract_text` with `include_notes=true`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |
| slides | string | no | 1-based slide spec; omit for every slide. |

## Returns
```
{
  ok: true,
  data: {
    slide_count: <int>,
    slides_with_notes: <int>,
    slides: [{ slide: <1-based>, notes: <str> }, ...]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `python-pptx` is not installed.
- `slide_out_of_range` / `invalid_input` — bad `slides` spec.

## Examples
### All notes
Call: `pptx.extract_notes(path="/tmp/deck.pptx")`

### Notes for slides 3-7
Call: `pptx.extract_notes(path="/tmp/deck.pptx", slides="3-7")`

## See also
- `pptx.extract_text` — full slide content plus optional notes.
