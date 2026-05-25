---
tool: pptx.split
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, split]
---

# pptx.split

## Purpose
Extract a subset of slides from a deck (or reorder them) into a new
`.pptx` file. Preserves the deck's slide master, theme, and the order
given in `slides=`.

## When to use
- The user wants to keep slides 1-5 / 3,7,9 only.
- A skill needs to reorder slides (pass them in the new order).
- You need to share a single section of a long deck.

## When NOT to use
- To combine multiple decks — use `pptx.merge`.
- To author a brand-new deck — use `pptx.create`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pptx` file. |
| slides | string | yes | 1-based slide spec to keep, e.g. `"1-5"` or `"1,3,7-9"`. Order is preserved. |
| output | string | yes | Destination `.pptx` path. |
| overwrite | bool | no | If true, replace the output file if it already exists. |

## Returns
```
{
  ok: true,
  data: {
    output: "<path>",
    slide_count: <int>,
    selected_slides: [<1-based slide numbers in output order>, ...]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — output doesn't end in `.pptx`, or `slides` spec is empty.
- `output_exists` — destination exists and `overwrite=false`.
- `slide_out_of_range` — `slides` spec refers to a missing slide.
- `split_failed` — XML manipulation failed (rare; message includes cause).
- `dependency_missing` — `python-pptx` is not installed.

## Examples
### Keep first five
Call: `pptx.split(path="/tmp/deck.pptx", slides="1-5", output="/tmp/intro.pptx")`

### Reorder
Call: `pptx.split(path="/tmp/deck.pptx", slides="3,1,2", output="/tmp/reordered.pptx")`

## See also
- `pptx.merge` — combine multiple decks.
- `pptx.read` — slide count before choosing a range.
