---
tool: pdf.decrypt
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, security]
---

# pdf.decrypt

## Purpose
Open a password-protected PDF using the supplied password and write an
unencrypted copy to a new path.

## When to use
- The user knows the password and wants an unencrypted copy of the document.
- A skill needs to call other PDF tools that cannot operate on encrypted input.

## When NOT to use
- To *guess* a password — this tool only accepts a known one. Do not loop.
- For PDFs that aren't actually encrypted — copy the file directly instead.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the encrypted `.pdf`. |
| password | string | yes | Password that opens the file. |
| output | string | yes | Destination `.pdf` path (will be unencrypted). |
| overwrite | bool | no | Replace existing destination. Default false. |

## Returns
On success: `{ok: true, data: {output, page_count}}`

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `password_required` — supplied password did not unlock the file.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Remove a password
Call: `pdf.decrypt(path="/tmp/secure.pdf", password="hunter2", output="/tmp/open.pdf")`

## See also
- `pdf.encrypt` — add a password.
- `pdf.read` — verify whether a file is encrypted before calling this.
