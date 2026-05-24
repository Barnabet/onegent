---
tool: pdf.encrypt
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, security]
---

# pdf.encrypt

## Purpose
Add password protection to a PDF and write the protected copy to a new path.

## When to use
- The user wants to send a PDF that opens only with a password.
- A skill must apply standard password protection before handing a file off.

## When NOT to use
- To remove a password — use `pdf.decrypt`.
- To restrict permissions only (printing, copying) while leaving the file
  openable — that requires fine-grained owner permissions which this tool
  does not expose; ask the user for an alternative if they need that.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pdf`. |
| user_password | string | yes | Password the recipient will type to open the PDF. |
| owner_password | string | no | Password for permissions changes. Defaults to `user_password`. |
| output | string | yes | Destination `.pdf` path. |
| overwrite | bool | no | Replace existing destination. Default false. |

## Returns
On success: `{ok: true, data: {output, page_count}}`

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — `user_password` missing, or `output` doesn't end in `.pdf`.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Add a password
Call: `pdf.encrypt(path="/tmp/memo.pdf", user_password="hunter2", output="/tmp/memo-secure.pdf")`

## See also
- `pdf.decrypt` — strip the password.
- `pdf.read` — check whether a PDF is already encrypted.
