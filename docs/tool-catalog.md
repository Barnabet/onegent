# Tool catalog

Generated from the live tool registry. Do not edit by hand.
Re-render with `python scripts/check_catalog.py --write`.

**25 tools** across **7 domains**.

## By domain

### `core`

#### `core.echo` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: core.echo
version: 1
owner: team-platform-ai
classification: [public]
tags: [diagnostic, smoke-test]
---

# core.echo

## Purpose
Return the input string unchanged. Used only for smoke-tests of the agent
loop and tool plumbing.

## When to use
- The user asks you to "echo" a specific string back to them verbatim.
- A skill explicitly instructs you to call `core.echo` as a connectivity check.

## When NOT to use
- For any real task. This tool does no useful work.
- To repeat the user's message back in a conversational reply — just include
  the text in your own response, no tool call needed.

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The exact string to echo back. Keep it short (< 200 chars). |

## Returns
On success: `{ok: true, data: {echoed: "<text>"}}`

## Errors
- `invalid_input` — `text` missing or not a string.

## Examples
### Smoke-test call
Call: `core.echo(text="hello")`
Returns: `{ok: true, data: {echoed: "hello"}}`

## See also
- (none — this tool exists in isolation for diagnostics.)

</details>

### `docstore`

#### `docstore.fetch` &nbsp; <sub>v1 · confidential · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: docstore.fetch
version: 1
owner: team-platform-ai
classification: [confidential]
tags: [docstore, fetch, read, internal-docs]
---

# docstore.fetch

## Purpose
Retrieve a document from the bank's internal document store by id, entity
name, or short free-text query. Returns the document body plus metadata.

## When to use
- A skill needs to pull a specific internal document — a KYC dossier, a
  credit file, a counterparty profile — to operate on it.
- The user gives you an entity name or an id and asks you to "fetch" or
  "pull up" the dossier.

## When NOT to use
- For searching the open web — use `web.search` (when available).
- For reading repository docs (authoring guides, catalogs) — use
  `repo.read_doc`.
- For reading a local spreadsheet path the user has attached — use
  `xlsx.read` or `text.read_file` (when available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| query | string | yes | An id (e.g. `"globex-kyc-2025"`), an entity name, or a short free-text term. |
| doc_type | string | no | Restrict to a specific type, e.g. `"kyc_dossier"`, `"credit_input"`. |
| latest | bool | no | When multiple match, return the most recently published. Default `true`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    id: "...",
    doc_type: "...",
    entity: "...",
    published: "YYYY-MM-DD",
    body: "<full document text>"
  }
}
```

## Errors
- `store_empty` — the document store is empty (configuration issue).
- `not_found` — no document matched the query.
- `file_missing` — the index references a file that is not on disk.

## Examples
### Fetch a KYC dossier by entity name
Call: `docstore.fetch(query="Globex Corporation", doc_type="kyc_dossier")`
Returns: `{ok: true, data: {id: "globex-kyc-2025", entity: "Globex Corporation SA", ...}}`

### Fetch a credit input file by id
Call: `docstore.fetch(query="acme-credit-input")`

## See also
- `repo.read_doc` — for repository docs, not internal documents.
- `xlsx.read` — when the user has attached an .xlsx file directly.

</details>

### `orchestrator`

#### `orchestrator.delegate` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: orchestrator.delegate
version: 1
owner: team-platform-ai
classification: [public]
tags: [routing, meta]
---

# orchestrator.delegate

## Purpose
Hand off a self-contained sub-task to a specialist pack. The specialist
runs in a fresh sub-agent loop with its own skills and tools, then
returns its final text reply and a summary of what it did.

## When to use
- The user's request maps to a single specialist pack from
  `orchestrator.list_packs`. Pick the best one and delegate.
- The user's request needs multiple specialists. Delegate to each one in
  turn with the relevant sub-task; combine their answers yourself.

## When NOT to use
- For pure conversational replies ("hi", "what can you do?") — answer
  yourself. Do not delegate trivia.
- To call a pack that is not in the allowed list — the call will fail
  with `pack_not_allowed`.
- To pass the user's raw message verbatim when it contains context the
  specialist does not need. Rewrite the sub-task to be self-contained.

## Parameters
| name | type | required | description |
|---|---|---|---|
| pack | string | yes | The pack name to delegate to. Must be in `allowed_packs`. |
| message | string | yes | A self-contained sub-task for the specialist. Include all context it needs — it cannot see the parent conversation. |

## Returns
On success: `{ok: true, data: {pack, final_text, stats: {turns, tool_calls, finish_reason}}}`

`final_text` is the specialist's last reply. Quote it or summarise it for
the user. The full event stream from the sub-agent is also forwarded
into the parent run's audit log automatically — you do not need to
re-emit it.

## Errors
- `pack_not_allowed` — `pack` is not in the router's `allowed_packs`.
- `pack_not_found` — `pack` does not exist.
- `subagent_failed` — the specialist raised; `error.message` has detail.

## Examples
### Routing a credit memo request
Call: `orchestrator.delegate(pack="credit_analyst", message="Draft a credit memo for Acme SpA. Financials: /tmp/acme.xlsx")`
Returns: `{ok: true, data: {pack: "credit_analyst", final_text: "Memo drafted...", stats: {turns: 4, tool_calls: 3, finish_reason: "stop"}}}`

### Smoke-test
Call: `orchestrator.delegate(pack="hello", message="ping")`
Returns: `{ok: true, data: {pack: "hello", final_text: "Platform is alive...", stats: {...}}}`

## See also
- `orchestrator.list_packs` — see which packs are available first.

</details>

#### `orchestrator.list_packs` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: orchestrator.list_packs
version: 1
owner: team-platform-ai
classification: [public]
tags: [routing, meta]
---

# orchestrator.list_packs

## Purpose
List the specialist packs the router is allowed to delegate to. Returns
each pack's name + one-line description so the model can pick the right
one for a user request.

## When to use
- At the start of a router run, to see what specialists are available.
- When the user asks a new question and you need to decide which
  specialist (if any) should handle it.

## When NOT to use
- If you have already called this in the current turn — the list does not
  change mid-run. Cache the answer.
- For pure conversational replies that do not need a specialist.

## Parameters
(none)

## Returns
On success: `{ok: true, data: {packs: [{name, description, classification}, ...]}}`

## Errors
- `no_router_context` — this tool was called outside a router run
  (no `allowed_packs` configured). Should not happen in practice.

## Examples
### Discovering specialists
Call: `orchestrator.list_packs()`
Returns: `{ok: true, data: {packs: [
  {name: "credit_analyst", description: "Pilot pack for credit analysts...", classification: "confidential"},
  {name: "hello", description: "Smoke-test pack...", classification: "public"}
]}}`

## See also
- `orchestrator.delegate` — actually invoke a specialist with a sub-task.

</details>

### `pdf`

#### `pdf.decrypt` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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

</details>

#### `pdf.encrypt` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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

</details>

#### `pdf.extract_tables` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pdf.extract_tables
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, tabular]
---

# pdf.extract_tables

## Purpose
Detect tables in a PDF and return their cell contents as 2-D arrays. Uses
`pdfplumber`'s line-based detection.

## When to use
- The user asks for the rows of a table in a PDF (e.g. a financial table, a
  rate sheet, a roster).
- A skill needs structured tabular data that exists *inside* a PDF rather
  than its own spreadsheet.

## When NOT to use
- For prose — use `pdf.extract_text`.
- For data that is rendered as an image (scanned tables) — use `pdf.ocr` and
  then parse the resulting text manually. Table detection on a scan returns
  nothing.
- If the source is a real `.xlsx` or `.csv`, never round-trip via PDF; use
  `xlsx.read` directly.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pdf` file. |
| pages | string | no | 1-based page spec; omit for every page. |

## Returns
On success:
```
{
  ok: true,
  data: {
    table_count: <int>,
    tables: [
      {page: <1-based>, index: <1-based within page>, row_count, col_count, rows: [[cell, ...], ...]},
      ...
    ]
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file is not a readable PDF.
- `dependency_missing` — `pdfplumber` is not installed.
- `page_out_of_range` / `invalid_input` — bad `pages` spec.
- `extraction_failed` — pdfplumber raised while parsing.

## Examples
### Tables on page 4
Call: `pdf.extract_tables(path="/tmp/rates.pdf", pages="4")`

### All tables in the document
Call: `pdf.extract_tables(path="/tmp/rates.pdf")`

## See also
- `pdf.extract_text` — for prose content.
- `xlsx.read` — when the source is actually a spreadsheet.
- `pdf.see` — visually confirm where the tables are before extracting.

</details>

#### `pdf.extract_text` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pdf.extract_text
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, text]
---

# pdf.extract_text

## Purpose
Extract the textual content of a PDF, page by page. Uses `pdfplumber` when
available (layout-aware), falls back to `pypdf` otherwise.

## When to use
- The user wants the prose / written content of a PDF.
- A skill needs the text body to summarise, search, or feed downstream.
- You can scope to a page range with `pages` to keep the response small.

## When NOT to use
- For tables — use `pdf.extract_tables`; running `extract_text` on a table
  produces a column-jumbled mess.
- For scanned PDFs that have no embedded text layer — use `pdf.ocr`. A first
  hint: `extract_text` returns empty strings or whitespace only.
- To *look* at the page (e.g. understand a chart) — use `pdf.see`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pdf` file. |
| pages | string | no | 1-based page spec, e.g. `"1"`, `"1-3"`, `"1,3-5,8"`. Omit for every page. |
| preserve_layout | bool | no | If true and pdfplumber is available, preserves columns/whitespace. Default false. |

## Returns
On success:
```
{
  ok: true,
  data: {
    backend: "pdfplumber" | "pypdf",
    page_count: <int>,
    char_count: <int>,
    pages: [{page: <1-based>, text: "..."}, ...]
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file is not a readable PDF.
- `page_out_of_range` — `pages` spec references pages outside `1..page_count`.
- `invalid_input` — `pages` spec is malformed.
- `extraction_failed` — the backend raised while parsing the PDF.

## Examples
### Extract everything
Call: `pdf.extract_text(path="/tmp/report.pdf")`

### Extract pages 1 to 3 only
Call: `pdf.extract_text(path="/tmp/report.pdf", pages="1-3")`

### Extract with column layout preserved
Call: `pdf.extract_text(path="/tmp/two-col.pdf", preserve_layout=true)`

## See also
- `pdf.extract_tables` — for structured tabular content.
- `pdf.ocr` — for scanned PDFs with no text layer.
- `pdf.see` — render pages as images to read visual content.

</details>

#### `pdf.fill_form` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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

</details>

#### `pdf.form_fields` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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

</details>

#### `pdf.merge` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pdf.merge
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, combine]
---

# pdf.merge

## Purpose
Concatenate two or more PDFs into a single output file, preserving page order.

## When to use
- The user wants to "combine", "merge", or "join" several PDFs into one.
- A skill produced multiple PDFs (e.g. one per section) and needs to deliver
  a single document.

## When NOT to use
- To pick a subset of pages from one PDF — use `pdf.split` instead.
- To overlay a watermark — that's a different operation; merge concatenates,
  it does not stamp.
- To merge a `.docx` and a `.pdf` — first convert the docx via a docx tool,
  then merge.

## Parameters
| name | type | required | description |
|---|---|---|---|
| inputs | string[] | yes | At least 2 paths to existing `.pdf` files, in concat order. |
| output | string | yes | Destination path; must end in `.pdf`. |
| overwrite | bool | no | If true, replace an existing `output` file. Default false. |

## Returns
On success: `{ok: true, data: {output, page_count, source_count}}`

## Errors
- `file_not_found` — one of the `inputs` does not exist.
- `unsupported_format` — one of the `inputs` is not a readable PDF.
- `invalid_input` — fewer than 2 inputs, or `output` doesn't end in `.pdf`.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Merge two PDFs
Call: `pdf.merge(inputs=["/tmp/a.pdf","/tmp/b.pdf"], output="/tmp/ab.pdf")`

### Merge three PDFs, replacing the destination
Call: `pdf.merge(inputs=["/tmp/cover.pdf","/tmp/body.pdf","/tmp/appendix.pdf"], output="/tmp/full.pdf", overwrite=true)`

## See also
- `pdf.split` — extract a page range.
- `pdf.rotate` — fix orientation before merging.

</details>

#### `pdf.ocr` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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

</details>

#### `pdf.read` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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

</details>

#### `pdf.rotate` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pdf.rotate
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, transform]
---

# pdf.rotate

## Purpose
Rotate one or more pages of a PDF by a multiple of 90 degrees and write the
result to a new file.

## When to use
- A scanned PDF arrived with pages sideways or upside-down.
- The user explicitly asks to rotate page N by 90/180/270 degrees.

## When NOT to use
- To resize or crop pages — rotation only changes orientation, not geometry.
- To rotate an image embedded in the PDF — that's an image-editing task; this
  tool rotates whole pages.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pdf`. |
| pages | string | no | 1-based page spec to rotate. Omit to rotate every page. |
| degrees | int | yes | One of `90`, `180`, `270`, `-90`, `-180`, `-270`. |
| output | string | yes | Destination `.pdf` path. |
| overwrite | bool | no | Replace existing destination. Default false. |

## Returns
On success: `{ok: true, data: {output, rotated_pages: [int, ...], degrees}}`

## Errors
- `file_not_found` / `unsupported_format` — bad input file.
- `invalid_input` — `degrees` not in the allowed set, or `pages` spec malformed.
- `page_out_of_range` — `pages` references pages that don't exist.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Rotate the whole document 90° clockwise
Call: `pdf.rotate(path="/tmp/scan.pdf", degrees=90, output="/tmp/scan-up.pdf")`

### Rotate just page 3
Call: `pdf.rotate(path="/tmp/scan.pdf", pages="3", degrees=180, output="/tmp/scan-fix.pdf")`

## See also
- `pdf.split` — extract a subset of pages.
- `pdf.see` — confirm orientation visually.

</details>

#### `pdf.see` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pdf.see
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, vision]
---

# pdf.see

## Purpose
Rasterise up to 5 pages of a PDF and inject them into the conversation as
images, so the model can *look* at the page rather than only parse its text.

## When to use
- The user asks about a chart, figure, diagram, signature, stamp, or layout
  feature that text extraction cannot recover.
- `pdf.extract_text` returned empty / nonsensical content and you suspect a
  scan — use `pdf.see` to confirm visually before reaching for `pdf.ocr`.
- The user wants you to compare two pages side by side and judge visual
  similarity.

## When NOT to use
- For the plain text body — `pdf.extract_text` is faster and feeds richer
  content per token.
- For tables that have an embedded text layer — `pdf.extract_tables` returns
  the cells directly. `pdf.see` is for the visual content only.
- To process many pages at once — this tool refuses more than 5 pages per
  call (`too_many_pages`). Call it twice if you must, but consider whether
  the user really needs all of them.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pdf` file. |
| pages | string | no | 1-based page spec; max 5 pages, e.g. `"1"`, `"2-4"`, `"1,3,5"`. Omit to render page 1. |
| scale | float | no | Render scale; `2.0` ≈ 200 dpi. Keep ≤ `3.0` to stay within model image limits. Default `2.0`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved>",
    page_count: <total pages in document>,
    rendered: [{page: <1-based>, bytes: <b64 length>}, ...],
    scale: <float>
  },
  images: [ToolImage, ...]   // attached to the next turn as multimodal content
}
```
The framework automatically appends the images to the next user turn so the
model can see them. The `data` payload itself is the textual summary.

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdfium2` is not installed.
- `page_out_of_range` / `invalid_input` — bad `pages` spec.
- `too_many_pages` — more than 5 pages requested in a single call.
- `render_failed` — the renderer raised on a specific page.

## Examples
### See page 1
Call: `pdf.see(path="/tmp/report.pdf")`

### See pages 2-4 of a deck
Call: `pdf.see(path="/tmp/slides.pdf", pages="2-4")`

### See three scattered pages
Call: `pdf.see(path="/tmp/big.pdf", pages="1,5,12")`

## See also
- `pdf.extract_text` — far cheaper for text content.
- `pdf.ocr` — when you need the text *of* a scanned page, not just to look at it.
- `pdf.read` — to know `page_count` before choosing pages to render.

</details>

#### `pdf.split` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pdf.split
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, split]
---

# pdf.split

## Purpose
Extract a subset of pages from a PDF into a new file. The selected pages keep
their original order in the destination.

## When to use
- The user wants a specific page range from a larger PDF.
- A skill needs to produce a smaller artefact (e.g. just the executive summary).

## When NOT to use
- To produce one PDF per page — call `pdf.split` once per page with the
  desired `pages` value, or write a thin loop in your skill workflow.
- To concatenate PDFs — use `pdf.merge`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pdf` file. |
| pages | string | yes | 1-based page spec to keep, e.g. `"1-5"` or `"1,3,7-9"`. |
| output | string | yes | Destination `.pdf` path. |
| overwrite | bool | no | If true, replace an existing `output` file. Default false. |

## Returns
On success: `{ok: true, data: {output, page_count, selected_pages: [1,2,...]}}`

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — file is not a readable PDF.
- `page_out_of_range` / `invalid_input` — `pages` spec is bad.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdf` is not installed.

## Examples
### Keep pages 1 through 5
Call: `pdf.split(path="/tmp/big.pdf", pages="1-5", output="/tmp/first5.pdf")`

### Keep a scattered selection
Call: `pdf.split(path="/tmp/big.pdf", pages="1,3,7-9", output="/tmp/sel.pdf")`

## See also
- `pdf.merge` — recombine extracts.
- `pdf.see` — verify what is on a page before splitting.

</details>

### `repo`

#### `repo.read_catalog` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.read_catalog
version: 1
owner: team-platform-ai
classification: [public]
tags: [catalog, read, reference]
---

# repo.read_catalog

## Purpose
Return the live catalog of every registered tool and discovered skill as
structured data: names, owners, classifications, tags, and purpose lines.

## When to use
- A skill needs to know what tools exist (e.g. the skill_creator before
  proposing a new tool).
- You need a quick inventory before deciding what to build.

## When NOT to use
- When you want to find tools matching a specific need — use
  `repo.search_catalog`, which scores by relevance.
- When you want the raw markdown of a tool card — read the card directly via
  the catalog entry's tool name + your knowledge of the layout, or browse
  `docs/tool-catalog.md` rendered output.

## Parameters
_(none)_

## Returns
On success:
```
{
  ok: true,
  data: {
    tools: [
      {name, version, owner, classification, tags, domain, purpose},
      ...
    ],
    skills: [
      {name, version, description},
      ...
    ]
  }
}
```

## Errors
_(none — the tool always succeeds with the current state.)_

## Examples
### Inventory before scaffolding
Call: `repo.read_catalog()`
Returns: `{ok: true, data: {tools: [...], skills: [...]}}`

## See also
- `repo.search_catalog` — relevance-scored lookup, preferred for dedup checks.
- `repo.read_doc` — read raw markdown from `docs/`.

</details>

#### `repo.read_doc` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.read_doc
version: 1
owner: team-platform-ai
classification: [public]
tags: [docs, read, reference]
---

# repo.read_doc

## Purpose
Read a markdown file from the repository's `docs/` directory and return its
full contents.

## When to use
- A skill needs to consult the authoring guides at runtime (e.g. the
  skill_creator reads `authoring-tools.md` before guiding the user).
- The user asks "what does the authoring guide say about X" and the answer
  lives in `docs/`.

## When NOT to use
- For reading anything outside `docs/` — this tool refuses out-of-tree paths.
- For reading a skill's `references/*.md` — use `repo.read_doc` only against
  the top-level `docs/` directory; references are loaded by the framework
  itself when a skill activates.
- For reading the live tool/skill catalog data — use `repo.read_catalog`,
  which returns structured JSON, not raw markdown.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path relative to `docs/`, e.g. `"authoring-tools.md"` or `"example-kyc-screening.md"`. |

## Returns
On success: `{ok: true, data: {path: "docs/...", content: "<full markdown>"}}`

## Errors
- `path_outside_docs` — path attempts to escape `docs/`.
- `not_found` — no such file under `docs/`.

## Examples
### Read the tool-authoring guide
Call: `repo.read_doc(path="authoring-tools.md")`
Returns: `{ok: true, data: {path: "docs/authoring-tools.md", content: "# Authoring tools\n..."}}`

### Read the worked example
Call: `repo.read_doc(path="example-kyc-screening.md")`

## See also
- `repo.read_catalog` — structured tool/skill list, not raw markdown.
- `repo.search_catalog` — find tools by name/tag/description.

</details>

#### `repo.scaffold_pack` &nbsp; <sub>v1 · internal · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.scaffold_pack
version: 1
owner: team-platform-ai
classification: [internal]
tags: [scaffold, write, pack-authoring]
---

# repo.scaffold_pack

## Purpose
Create a new pack YAML at `packs/<name>.yaml` that bundles one or more
existing skills for a persona.

## When to use
- The skill_creator skill has confirmed the persona, the list of skills,
  the classification ceiling, and the model id.

## When NOT to use
- If any listed skill does not exist — create the skills first using
  `repo.scaffold_skill`.
- To modify an existing pack — this tool refuses overwrites.
- For packs at `confidential` or above without first agreeing on a risk
  review process — this tool will create the pack but will NOT fill in
  `risk_review` for you; the user must add it before the pack will load.

## Parameters
| name | type | required | description |
|---|---|---|---|
| name | string | yes | Pack name, lowercase + underscores. |
| owner | string | yes | Owning team. |
| description | string | yes | One paragraph on the persona this pack serves. |
| skills | list[string] | yes | Skill names already on disk. Validated. |
| classification | string | no | Default `internal`. |
| model | string | no | Pinned model id, default `claude-sonnet-4-6`. |
| allowed_data_sources | list[string] | no | Coarse allow-list. |

## Returns
On success:
```
{
  ok: true,
  data: {
    pack: "<name>",
    created: ["packs/<name>.yaml"],
    next_steps: [...]   # includes a reminder about risk_review for confidential+
  }
}
```

## Errors
- `invalid_name` — name contains invalid characters.
- `already_exists` — pack file already exists.
- `unknown_skills` — one or more listed skills are not on disk.

## Examples
### A simple internal-class pack
Call: `repo.scaffold_pack(name="credit_analyst", owner="team-credit-ai", description="Credit analysts drafting and reviewing corporate credit memos.", skills=["credit_memo", "xlsx_analysis"], classification="internal")`
Returns: `{ok: true, data: {pack: "credit_analyst", created: ["packs/credit_analyst.yaml"], next_steps: [...]}}`

## See also
- `repo.scaffold_skill` — create any missing skills first.
- `repo.scaffold_tool` — create any missing tools first.

</details>

#### `repo.scaffold_skill` &nbsp; <sub>v1 · internal · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.scaffold_skill
version: 1
owner: team-platform-ai
classification: [internal]
tags: [scaffold, write, skill-authoring]
---

# repo.scaffold_skill

## Purpose
Create a new skill folder under `skills/<name>/` with a templated `SKILL.md`
and a populated `manifest.yaml` listing the tools the skill will require.

## When to use
- The skill_creator skill has gathered the skill's intended name, owner,
  classification, and the list of tools it will use, and all those tools
  already exist in the catalog.

## When NOT to use
- If any required tool is missing from the catalog — instruct the user to
  create the missing tool(s) first using `repo.scaffold_tool`.
- To modify an existing skill — this tool refuses overwrites.

## Parameters
| name | type | required | description |
|---|---|---|---|
| name | string | yes | Skill name, lowercase + underscores. |
| owner | string | yes | Owning team. |
| requires_tools | list[string] | yes | Exact tool names the skill will call. Validated against the registry. |
| classification | string | no | One of `public`, `internal`, `confidential`, `restricted`. Default `internal`. |
| data_sources | list[string] | no | Coarse data-source allow-list for audit reporting. |

## Returns
On success:
```
{
  ok: true,
  data: {
    skill: "<name>",
    created: ["skills/<name>"],
    next_steps: [...]
  }
}
```

## Errors
- `invalid_name` — name contains invalid characters.
- `already_exists` — `skills/<name>/` already exists.
- `unknown_tools` — one or more requested tools are not registered.

## Examples
### A skill reusing existing tools
Call: `repo.scaffold_skill(name="kyc_screening", owner="team-financial-crime-ai", requires_tools=["docstore.fetch", "text.summarize", "web.adverse_media_search"], classification="confidential", data_sources=["internal_docs", "public_web"])`
Returns: `{ok: true, data: {skill: "kyc_screening", created: ["skills/kyc_screening"], next_steps: [...]}}`

## See also
- `repo.scaffold_tool` — create any missing tools first.
- `repo.scaffold_pack` — wrap the new skill into a persona pack.

</details>

#### `repo.scaffold_tool` &nbsp; <sub>v1 · internal · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.scaffold_tool
version: 1
owner: team-platform-ai
classification: [internal]
tags: [scaffold, write, tool-authoring]
---

# repo.scaffold_tool

## Purpose
Create the skeleton files for a new tool from the canonical template:
`registry.py`, `impl.py`, `cards/<verb>.md`, and a stub test file.

## When to use
- The skill_creator skill has confirmed (via `repo.search_catalog`) that the
  proposed tool does not duplicate an existing one, and the user has agreed
  on the name and owner.

## When NOT to use
- Before running a dedup check — always call `repo.search_catalog` first.
- To modify an existing tool — this tool only creates new artifacts and
  refuses overwrites.
- To create a tool in a domain you have not discussed with the user — the
  domain (`<domain>` in `<domain>.<verb>`) is a long-lived shared namespace
  and shouldn't be invented on the fly.

## Parameters
| name | type | required | description |
|---|---|---|---|
| name | string | yes | Full tool name as `<domain>.<verb>`, lowercase + underscores only. |
| owner | string | yes | Owning team, e.g. `"team-credit-ai"`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    tool: "<name>",
    created: ["tools/<domain>/", "tools/<domain>/cards/<verb>.md", ...],
    next_steps: [...]   # human-readable list of follow-ups
  }
}
```

## Errors
- `invalid_name` — name not `<domain>.<verb>` or contains invalid characters.
- `already_exists` — tool with that name is already registered, or the card
  file already exists.

## Examples
### First tool in a new domain
Call: `repo.scaffold_tool(name="email.send", owner="team-comms-ai")`
Returns: `{ok: true, data: {tool: "email.send", created: ["tools/email"], next_steps: [...]}}`

### Adding a new verb to an existing domain
Call: `repo.scaffold_tool(name="xlsx.add_chart", owner="team-doc-ai")`
Returns: `{ok: true, data: {tool: "xlsx.add_chart", created: ["tools/xlsx/cards/add_chart.md"], next_steps: [...]}}`

## See also
- `repo.search_catalog` — call first to confirm no duplicate.
- `repo.scaffold_skill` — for new skills.

</details>

#### `repo.search_catalog` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: repo.search_catalog
version: 1
owner: team-platform-ai
classification: [public]
tags: [catalog, search, dedup]
---

# repo.search_catalog

## Purpose
Search the live tool catalog by free-text query and return ranked hits with
their purpose lines, tags, and owners. Used primarily as a dedup check
before proposing a new tool.

## When to use
- Before scaffolding a new tool, search for near-duplicates the author may
  have missed.
- A skill author is picking tools for a workflow step and wants candidates.

## When NOT to use
- For listing every tool — use `repo.read_catalog`, which returns the full
  inventory without scoring.
- For reading the actual card body of a specific tool — fetch via the
  catalog entry name.

## Parameters
| name | type | required | description |
|---|---|---|---|
| query | string | yes | Free-text, e.g. `"read excel"`, `"summarize text"`, `"docstore"`. Lower-case match. |
| limit | int | no | Max hits returned, default 8, max 50. |

## Returns
On success:
```
{
  ok: true,
  data: {
    query: "<echoed>",
    hits: [
      {name, score, tags, purpose, owner},
      ...   # sorted by score desc
    ]
  }
}
```

## Errors
- `empty_query` — query is empty or whitespace-only.

## Examples
### Dedup check before adding `xlsx.read_sheet`
Call: `repo.search_catalog(query="read excel")`
Returns: `{ok: true, data: {query: "read excel", hits: [{name: "xlsx.read", score: 0.95, ...}, ...]}}`

### Browse summarization tools
Call: `repo.search_catalog(query="summarize", limit=5)`

## See also
- `repo.read_catalog` — full inventory, unranked.
- `repo.scaffold_tool` — call after confirming no duplicate exists.

</details>

### `text`

#### `text.extract_lines` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: text.extract_lines
version: 1
owner: team-platform-ai
classification: [public]
tags: [text, extract, numeric, deterministic]
---

# text.extract_lines

## Purpose
Scan a text and return the subset of lines that contain numbers, percentages,
currency amounts, or `Key: value` patterns. Deterministic, no LLM. The
returned lines are the raw material a skill can summarize or cite.

## When to use
- A skill is processing a free-form document (credit input, KYC dossier,
  research note) and needs to surface the quantitative / structured lines.
- Before drafting a summary, to give the model a ranked candidate set of
  lines worth quoting verbatim.

## When NOT to use
- For producing a prose summary — the skill itself should do that using
  the lines this tool returns. There is no LLM-summarization tool by design.
- For parsing structured spreadsheets — use `xlsx.read`.
- For extracting tables out of a PDF — use `pdf.extract_tables` (when
  available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The text to scan. |
| kinds | list[string] | no | Subset of `numeric`, `percentage`, `currency`, `key_value`. Default: all four. |

## Returns
On success:
```
{
  ok: true,
  data: {
    lines: [
      {line_no: 4, text: "Revenue: EUR 412m (+8.2% YoY)", kinds: ["numeric","percentage","currency","key_value"]},
      ...
    ],
    total_matched: 7
  }
}
```

## Errors
- `empty_input` — the text was empty or whitespace-only.

## Examples
### Surface numeric lines from a credit file
Call: `text.extract_lines(text="<credit file body>")`
Returns: `{ok: true, data: {lines: [{line_no: 4, text: "Revenue: EUR 412m ...", kinds: [...]}, ...], total_matched: 6}}`

### Only key:value lines
Call: `text.extract_lines(text="...", kinds=["key_value"])`

## See also
- `text.word_count` — basic metrics.
- `xlsx.read` — when the source is tabular, not prose.

</details>

#### `text.word_count` &nbsp; <sub>v1 · public · owner: team-platform-ai</sub>

<details><summary>card</summary>

---
tool: text.word_count
version: 1
owner: team-platform-ai
classification: [public]
tags: [text, metrics, deterministic]
---

# text.word_count

## Purpose
Return the number of words and characters in a piece of text.

## When to use
- A skill needs to check whether a draft fits a length budget before
  returning it.
- Quick sanity check on a document's size before deciding whether to chunk it.

## When NOT to use
- For token counting against a specific model — this tool returns word
  count, not tokens.
- For extracting structured content — use `text.extract_lines`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The text to measure. |

## Returns
On success: `{ok: true, data: {words: <int>, chars: <int>}}`

## Errors
_(none)_

## Examples
### Measure a draft
Call: `text.word_count(text="...")`
Returns: `{ok: true, data: {words: 412, chars: 2890}}`

## See also
- `text.extract_lines` — for content-level extraction.

</details>

### `xlsx`

#### `xlsx.read` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.read
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, tabular]
---

# xlsx.read

## Purpose
Read a spreadsheet file (`.xlsx`, `.xlsm`, `.csv`, or `.tsv`) and return its
contents as a header row + list of data rows.

## When to use
- The user gives you a path to a spreadsheet and asks you to inspect, analyse,
  or summarise its contents.
- A skill needs the rows from a workbook before doing any analysis on them.

## When NOT to use
- For writing or modifying a workbook — not supported yet; will be `xlsx.write_*`.
- For complex pivot / chart inspection — not supported; returns raw cell values.
- For reading PDFs of spreadsheet exports — use `pdf.extract_tables` (when
  available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Absolute or relative path to the file. |
| sheet | string | no | Sheet name (xlsx only). Defaults to the first sheet. |
| has_header | bool | no | If true (default), the first row becomes `headers`; otherwise it stays in `rows`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    sheet: "<name>",
    headers: ["col1", "col2", ...] | null,
    rows: [[v1, v2, ...], ...],
    row_count: <int>
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — extension not in `.xlsx`, `.xlsm`, `.csv`, `.tsv`.
- `sheet_not_found` — requested sheet name is not in the workbook.
- `dependency_missing` — openpyxl is not installed in this environment.

## Examples
### Read default sheet of an xlsx
Call: `xlsx.read(path="/data/loans.xlsx")`
Returns: `{ok: true, data: {sheet: "Sheet1", headers: ["id","amount"], rows: [["L1",100], ...], row_count: 20}}`

### Read a specific sheet
Call: `xlsx.read(path="/data/loans.xlsx", sheet="Q1")`

### Read a CSV
Call: `xlsx.read(path="/data/loans.csv")`

## See also
- `text.extract_lines` — for prose, not tabular sources.
- `docstore.fetch` — when the source is internally stored rather than at a path.

</details>

## By tag

- **catalog** — `repo.read_catalog`, `repo.search_catalog`
- **combine** — `pdf.merge`
- **dedup** — `repo.search_catalog`
- **deterministic** — `text.extract_lines`, `text.word_count`
- **diagnostic** — `core.echo`
- **docs** — `repo.read_doc`
- **docstore** — `docstore.fetch`
- **extract** — `text.extract_lines`
- **fetch** — `docstore.fetch`
- **forms** — `pdf.fill_form`, `pdf.form_fields`
- **internal-docs** — `docstore.fetch`
- **meta** — `orchestrator.delegate`, `orchestrator.list_packs`
- **metadata** — `pdf.read`
- **metrics** — `text.word_count`
- **numeric** — `text.extract_lines`
- **ocr** — `pdf.ocr`
- **pack-authoring** — `repo.scaffold_pack`
- **pdf** — `pdf.decrypt`, `pdf.encrypt`, `pdf.extract_tables`, `pdf.extract_text`, `pdf.fill_form`, `pdf.form_fields`, `pdf.merge`, `pdf.ocr`, `pdf.read`, `pdf.rotate`, `pdf.see`, `pdf.split`
- **read** — `docstore.fetch`, `pdf.extract_tables`, `pdf.extract_text`, `pdf.form_fields`, `pdf.ocr`, `pdf.read`, `pdf.see`, `repo.read_catalog`, `repo.read_doc`, `xlsx.read`
- **reference** — `repo.read_catalog`, `repo.read_doc`
- **routing** — `orchestrator.delegate`, `orchestrator.list_packs`
- **scaffold** — `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`
- **search** — `repo.search_catalog`
- **security** — `pdf.decrypt`, `pdf.encrypt`
- **skill-authoring** — `repo.scaffold_skill`
- **smoke-test** — `core.echo`
- **split** — `pdf.split`
- **spreadsheet** — `xlsx.read`
- **tabular** — `pdf.extract_tables`, `xlsx.read`
- **text** — `pdf.extract_text`, `text.extract_lines`, `text.word_count`
- **tool-authoring** — `repo.scaffold_tool`
- **transform** — `pdf.rotate`
- **vision** — `pdf.see`
- **write** — `pdf.decrypt`, `pdf.encrypt`, `pdf.fill_form`, `pdf.merge`, `pdf.rotate`, `pdf.split`, `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`
