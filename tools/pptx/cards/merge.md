---
tool: pptx.merge
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, combine]
---

# pptx.merge

## Purpose
Concatenate two or more `.pptx` files into a single deck. The output
inherits the slide master, theme, and slide size of the **first** input.
Slides from subsequent decks are appended in order; their shapes are
cloned onto a matching layout from the first deck (falling back to
"Blank" if no layout name matches).

## When to use
- The user wants to stitch together cover/body/appendix decks.
- A skill needs to bolt a programmatically-generated cover onto an
  existing deck.

## When NOT to use
- To rearrange slides inside a single deck — use `pptx.split` with a
  reordered `slides=` spec, then save as a new file.
- When you must preserve every decks' theme — `pptx.merge` standardises
  on the first input's theme. If themes diverge significantly, consider
  converting the others to images and rebuilding via `pptx.create`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| inputs | string[] | yes | List of `.pptx` paths, in the order to concatenate. At least 2. |
| output | string | yes | Destination `.pptx` path. |
| overwrite | bool | no | If true, replace the output file when it exists. |

## Returns
```
{
  ok: true,
  data: {
    output: "<path>",
    slide_count: <int>,
    source_count: <int>,
    appended: <int>   // slides added from inputs 2..N
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — fewer than 2 inputs, or output doesn't end in `.pptx`.
- `output_exists` — destination exists and `overwrite=false`.
- `merge_failed` — a slide copy failed (the message includes the source).
- `dependency_missing` — `python-pptx` is not installed.

## Examples
### Cover + body
Call:
```
pptx.merge(
  inputs=["/tmp/cover.pptx", "/tmp/body.pptx"],
  output="/tmp/full.pptx"
)
```

### Three-deck stitch with overwrite
Call:
```
pptx.merge(
  inputs=["/tmp/intro.pptx", "/tmp/main.pptx", "/tmp/appendix.pptx"],
  output="/tmp/full.pptx",
  overwrite=true
)
```

## See also
- `pptx.split` — extract a subset of slides into a new deck.
- `pptx.create` — author a fresh deck from structured data.
