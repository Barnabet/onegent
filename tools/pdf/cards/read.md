---
tool: pdf.read
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, metadata]
---

# pdf.read

## Purpose
Open a PDF and return its metadata, page count, and per-page geometry. Use
this first whenever you need to know how big a PDF is or what's in it before
calling a heavier extraction tool.

## When to use
- The user hands you a `.pdf` path and asks "what is this" or "how many pages".
- A skill needs the page count to drive a `pages=` argument in a follow-up
  call to `pdf.extract_text`, `pdf.split`, or `pdf.see`.
- You suspect a PDF is encrypted and want to confirm before trying to read it.

## When NOT to use
- For text content — use `pdf.extract_text`.
- For tables — use `pdf.extract_tables`.
- For visually inspecting the layout — use `pdf.see` (renders pages as images).
- For scanned PDFs that need OCR — use `pdf.ocr`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pdf` file. |
| password | string | no | Decryption password if the PDF is encrypted. |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved path>",
    page_count: <int or null if still encrypted>,
    encrypted: <bool>,
    metadata: { title, author, subject, creator, producer },
    pages: [{ index, width, height, rotation }, ...]
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file does not have a `.pdf` extension or is unreadable.
- `password_required` — PDF is encrypted and either no password was supplied,
  or the supplied one was wrong.
- `dependency_missing` — `pypdf` is not installed in this environment.

## Examples
### Inspect a PDF
Call: `pdf.read(path="/tmp/loan.pdf")`
Returns: `{ok: true, data: {page_count: 12, encrypted: false, metadata: {title: "Loan Memo"}, pages: [...]}}`

### Inspect an encrypted PDF
Call: `pdf.read(path="/tmp/secure.pdf", password="hunter2")`

## See also
- `pdf.extract_text` — the actual text content.
- `pdf.see` — rasterise pages as images for visual inspection.
- `pdf.decrypt` — strip encryption permanently.
