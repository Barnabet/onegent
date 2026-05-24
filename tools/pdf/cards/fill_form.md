---
tool: pdf.fill_form
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, forms]
---

# pdf.fill_form

## Purpose
Write values into the AcroForm text fields of a PDF and save the filled copy.

## When to use
- You have already called `pdf.form_fields` to get the field names, you have
  a mapping `{field_name: value}` ready, and the user wants the filled PDF.

## When NOT to use
- Before listing the fields — you need the exact field names from
  `pdf.form_fields`. Guessing field names produces a no-op.
- For PDFs without AcroForm fields — the tool returns `no_form_fields`. For
  flat scans of forms, you cannot fill them through this tool.
- For checkbox/radio/choice fields with cryptic value sets — the catalogue
  currently writes only string values into text fields; for richer field
  types you'll need a more specialised tool.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pdf`. |
| values | object | yes | Mapping of field name → value, e.g. `{"Name": "Jane"}`. |
| output | string | yes | Destination `.pdf` path. |
| overwrite | bool | no | Replace existing destination. Default false. |

## Returns
On success: `{ok: true, data: {output, filled_fields: ["Name", ...]}}`

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — `values` empty, or `output` doesn't end in `.pdf`.
- `no_form_fields` — PDF has no AcroForm fields to fill.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Fill name and date
Call: `pdf.fill_form(path="/tmp/w9.pdf", values={"Name":"Jane Doe","Date":"2026-05-24"}, output="/tmp/w9-filled.pdf")`

## See also
- `pdf.form_fields` — discover the field names first.
- `pdf.see` — visually confirm the filled output.
