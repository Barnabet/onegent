---
tool: pptx.convert
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, convert]
---

# pptx.convert

## Purpose
Convert a `.pptx` deck to a `.pdf` file using LibreOffice (`soffice`) in
headless mode. The resulting PDF has one page per slide and preserves
fonts/colours/charts well enough for almost any review purpose.

## When to use
- The user asks to "export the deck as PDF" / "share a PDF copy".
- A downstream skill needs a PDF rendering of the deck (e.g. to call
  `pdf.extract_text` for higher-fidelity text, or to attach to an email).
- You want to feed the deck into a tool that only accepts PDFs.

## When NOT to use
- For raster page images — use `pptx.see` instead (it goes through PDF
  too but returns PNG bytes ready for the model to look at).
- To extract slide text — `pptx.extract_text` is much faster and runs
  without LibreOffice.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |
| output | string | yes | Destination `.pdf` path (must end in `.pdf`). |
| overwrite | bool | no | If true, replace the output file if it already exists. |
| timeout_seconds | int | no | Hard limit on the LibreOffice subprocess (default 120). |

## Returns
```
{
  ok: true,
  data: {
    output: "<path>",
    size_bytes: <int>
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — `output` does not end in `.pdf`.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — LibreOffice (`soffice`) is not on `PATH`.
- `timeout` — LibreOffice did not finish within `timeout_seconds`.
- `convert_failed` — LibreOffice returned a non-zero exit code.

## Examples
### Export to PDF
Call: `pptx.convert(path="/tmp/deck.pptx", output="/tmp/deck.pdf")`

### Overwrite an existing PDF
Call: `pptx.convert(path="/tmp/deck.pptx", output="/tmp/deck.pdf", overwrite=true)`

## See also
- `pptx.see` — render selected slides as PNG images for visual inspection.
- `pdf.see`, `pdf.extract_text` — operate on the resulting PDF.
