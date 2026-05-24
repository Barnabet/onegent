---
tool: pdf.form_fields
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, forms]
---

# pdf.form_fields

## Purpose
List the fillable form fields embedded in a PDF (AcroForm fields). Returns
field names, types, and current values.

## When to use
- The user wants to *fill* a form and you need to know which fields exist.
- A skill must check whether a PDF is a true fillable form vs a flat scan of one.

## When NOT to use
- For a PDF that prints out a form to fill by hand — there are no AcroForm
  fields; you'd need to render the page with `pdf.see` and overlay the
  values another way (out of scope here).
- To actually write field values — use `pdf.fill_form`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the `.pdf` file. |

## Returns
On success:
```
{
  ok: true,
  data: {
    field_count: <int>,
    fillable: <bool>,   // true iff at least one AcroForm field exists
    text_fields: { "<name>": "<current value>" },
    fields: [{name, type, value}, ...]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### List the fields of a tax form
Call: `pdf.form_fields(path="/tmp/w9.pdf")`
Returns (abridged): `{ok: true, data: {field_count: 14, fillable: true, fields: [{name: "Name", type: "/Tx", value: null}, ...]}}`

## See also
- `pdf.fill_form` — write values into the fields you just discovered.
- `pdf.see` — visually inspect form layout when field names are cryptic.
