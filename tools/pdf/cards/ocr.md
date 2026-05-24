---
tool: pdf.ocr
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, ocr]
---

# pdf.ocr

## Purpose
Run Tesseract OCR over each requested page of a PDF and return the recognised
text per page. Use only when the PDF has no embedded text layer.

## When to use
- `pdf.extract_text` returned empty / whitespace-only strings for the pages
  the user cares about — that's the signature of a scan.
- The user explicitly describes the PDF as a "scan" or "image-only PDF".

## When NOT to use
- For PDFs with a real text layer — use `pdf.extract_text`. OCR is much
  slower and less accurate than reading embedded text.
- When the tesseract binary or `pytesseract` is unavailable — the tool will
  return `dependency_missing`; tell the user.
- For multi-language scans without telling the tool — pass `lang="eng+fra"`
  etc., otherwise non-default scripts come out as garbage.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the `.pdf` file. |
| pages | string | no | 1-based page spec; omit for every page. OCR is slow — narrow when you can. |
| lang | string | no | Tesseract language code; default `"eng"`. Examples: `"fra"`, `"deu"`, `"eng+fra"`. |
| scale | float | no | Render scale before OCR. Default `2.0` (~200 dpi). Higher = sharper but slower. |

## Returns
On success:
```
{
  ok: true,
  data: {
    page_count: <int>,
    lang: "<code>",
    pages: [{page: <1-based>, text: "..."}, ...]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdfium2`, `pytesseract`, or the tesseract binary
  is not available.
- `page_out_of_range` / `invalid_input` — bad `pages` spec.
- `ocr_failed` — tesseract raised on a page.

## Examples
### OCR a French scan, pages 1–3
Call: `pdf.ocr(path="/tmp/scan.pdf", pages="1-3", lang="fra")`

### OCR an English scan at higher resolution
Call: `pdf.ocr(path="/tmp/blurry.pdf", scale=3.0)`

## See also
- `pdf.extract_text` — always try this first.
- `pdf.see` — visually confirm that the PDF is indeed a scan.
