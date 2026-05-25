---
tool: html.to_pdf
version: 1
owner: team-doc-ai
classification: [internal]
tags: [html, write, convert]
---

# html.to_pdf

## Purpose
Convert an HTML file to PDF using LibreOffice (`soffice`) in headless
mode. Honours the `@media print` rules of the document, so reports
authored with `html.create` (which always emits a print-ready CSS block)
produce a clean A4 PDF with proper page breaks, hidden page chrome, and
table headers repeated on each page.

## When to use
- The user wants the report as a PDF (for email, signature, archival).
- A downstream skill needs a paginated copy (e.g. to attach to a memo).
- You want a fixed-layout snapshot of an interactive HTML artifact.

## When NOT to use
- For per-page image renders — use `html.see`.
- For tiny tweaks to an existing PDF — use the `pdf.*` family instead.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.html` / `.htm` file. |
| output | string | yes | Destination `.pdf` path. |
| overwrite | bool | no | If true, replace the output file if it already exists. |
| timeout_seconds | int | no | Hard limit on the LibreOffice subprocess (default 120). |

## Returns
```
{
  ok: true,
  data: { output: "<path>", size_bytes: <int> }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — `output` does not end in `.pdf`.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — LibreOffice (`soffice`) is not on `PATH`.
- `timeout` / `convert_failed` — LibreOffice failed.

## Examples
### Export
Call: `html.to_pdf(path="/tmp/report.html", output="/tmp/report.pdf")`

## See also
- `html.create` — author the HTML in the first place (it ships with a
  `@media print` block that this tool relies on).
- `html.see` — image renders for visual verification.
- `pdf.see`, `pdf.extract_text` — operate on the resulting PDF.
