# Tool catalog

Generated from the live tool registry. Do not edit by hand.
Re-render with `python scripts/check_catalog.py --write`.

**32 tools** across **7 domains**.

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
version: 2
owner: team-platform-ai
classification: [public]
tags: [routing, meta]
---

# orchestrator.delegate

## Purpose
Spawn a sub-agent to handle a self-contained sub-task. The sub-agent runs
in a fresh loop with its own skills and tools, then returns its final
text reply and a summary of what it did.

Three shapes are supported:

1. **Pack** — `pack="credit_analyst"`. The specialist runs with the
   pack's own skills. Use when a specialist already matches the task.
2. **Pack + extra skills** — `pack="credit_analyst", extra_skills=["pdf_handling"]`.
   Splice extra skills (from the composable-skills catalog in your
   system prompt) on top of the pack's skills. Use when a specialist is
   *almost* right but needs one more capability for this task.
3. **Skills only** — `skills=["pdf_handling", "xlsx_handling"]`, no `pack`.
   Ad-hoc sub-agent composed from individual skills, running under the
   router's own model / classification / limits. Use when no specialist
   fits but a combination of skills will.

## When to use
- The user's request maps to a single specialist pack from the
  delegatable-packs catalog in your system prompt. Pick it and delegate.
- The user's request needs a capability mix that no specialist provides.
  Compose it from the composable-skills catalog using `skills=[...]`.
- The user's request needs several skills working together on the SAME
  task. Send one sub-agent with all the relevant skills — do not split
  into multiple sub-agents unless the steps are genuinely independent
  (different files / no data flowing between them).

## When NOT to use
- For pure conversational replies ("hi", "what can you do?") — answer
  yourself. Do not delegate trivia.
- To call a pack outside `allowed_packs` — the call fails with
  `pack_not_allowed`. (Skills are not gated; pick any from the
  composable-skills catalog.)

## Parameters
| name | type | required | description |
|---|---|---|---|
| pack | string | one-of | Specialist pack name. Must be in `allowed_packs`. |
| skills | string[] | one-of | Skills for an ad-hoc sub-agent (no pack). Pick from the composable-skills catalog in the system prompt. |
| extra_skills | string[] | no | Extra skills to add on top of `pack`. Pick from the composable-skills catalog. Ignored without `pack`. |
| message | string | yes | Self-contained sub-task. Include all context — the sub-agent cannot see the parent conversation. |
| files | string[] | no | Conversation `file_id`s to forward. Omit/`null` = all attachments (default). `[]` = none. Subset = only those. Unknown ids are dropped. |

Exactly one of `pack` or `skills` must be set.

## Returns
On success: `{ok: true, data: {pack, skills, final_text, stats: {turns, tool_calls, finish_reason}}}`

`pack` is `null` for skills-only sub-agents. `skills` is the resolved
skill list actually bound on the sub-agent. `final_text` is the
sub-agent's last reply — quote it or summarise it for the user. The full
event stream is forwarded into the parent run's audit log automatically.

## Errors
- `invalid_input` — neither/both of `pack`/`skills` set, or `extra_skills`
  passed without `pack`.
- `pack_not_allowed` — `pack` not in `allowed_packs`.
- `pack_not_found` — `pack` does not exist on disk.
- `skill_not_found` / `skills_bind_failed` — a requested skill could not
  be loaded or its tools/classification could not be bound.
- `subagent_failed` — the sub-agent raised; `error.message` has detail.

## Examples
### Routing a credit memo request
Call: `orchestrator.delegate(pack="credit_analyst", message="Draft a credit memo for Acme SpA. Financials: /tmp/acme.xlsx")`
Returns: `{ok: true, data: {pack: "credit_analyst", skills: [...], final_text: "Memo drafted...", stats: {turns: 4, tool_calls: 3, finish_reason: "stop"}}}`

### Topping up a specialist with PDF reading
Call: `orchestrator.delegate(pack="credit_analyst", extra_skills=["pdf_handling"], message="...", files=["f_kbis"])`

### Skills-only ad-hoc sub-agent
Call: `orchestrator.delegate(skills=["pdf_handling", "xlsx_handling"], message="Cross-check the totals in /tmp/a.pdf against /tmp/b.xlsx", files=["f_pdf", "f_xlsx"])`
Returns: `{ok: true, data: {pack: null, skills: ["pdf_handling", "xlsx_handling"], final_text: "...", stats: {...}}}`

## See also
- The **Delegatable packs** and **Composable skills** sections of your
  system prompt list every pack and skill you may pass here.

</details>

### `pdf`

#### `pdf.create` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pdf.create
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, create, report]
---

# pdf.create

## Purpose
Author a brand-new PDF from a structured list of elements. Handles
covers, headings, paragraphs, tables (zebra / minimal / grid), bullets,
numbered lists, callouts (info / tip / note / success / warning /
danger), quotes, banners, KPI rows, cards, multi-column layouts,
badges / pills, bar / line / pie charts, flow diagrams, timelines,
images, raw shapes, horizontal rules, spacers, and explicit page
breaks. Pick a theme (default, professional, modern, minimal, vibrant,
dark) or pass a custom theme with `primary`/`secondary`/`accent`/
`text`/`muted`/`surface`/`border` hex colours.

Prefer this over shelling out to `reportlab` yourself: it already knows
the styling, the page templates, and the Unicode gotchas (sub/super
characters are auto-converted to `<sub>`/`<super>` tags so they don't
render as black boxes).

## When to use
- The user asks for a PDF report, summary, presentation, memo, or
  one-pager.
- A skill needs to materialise a structured output (KPIs, tables,
  charts, narrative sections) as a deliverable file.

## When NOT to use
- To modify an existing PDF: use `pdf.merge`, `pdf.split`, `pdf.rotate`,
  `pdf.fill_form`, etc.
- To "export" an Excel file as PDF: build the PDF from the *data* with
  this tool, don't try to round-trip a `.xlsx`.
- For raster output (PNG/JPG): not supported — render the PDF and use
  `pdf.see` if you need page images.

## Parameters
| name | type | required | description |
|---|---|---|---|
| output | string | yes | Destination `.pdf` path. Must end in `.pdf`. |
| elements | object[] | yes | Ordered list of element objects (see below). |
| theme | string \| object | no | Theme name or custom palette. Default `"default"`. |
| page_size | string | no | `"letter"` (default), `"A4"`, or `"legal"`. |
| margin | float | no | Uniform page margin in points. Default `54` (= 0.75 inch). |
| title | string | no | PDF metadata: title. |
| author | string | no | PDF metadata: author. |
| subject | string | no | PDF metadata: subject. |
| header | string \| object | no | Page header. String → centred. Object → `{left, center, right}`. |
| footer | string \| object | no | Page footer. Same shape as `header`. |
| page_numbers | bool | no | If true, draw `Page N` in the footer-right of every page. |
| overwrite | bool | no | If true, replace the output file if it already exists. |

## Element types

Each element is `{"type": "<name>", ...fields}`.

| type | required fields | notable optional fields |
|---|---|---|
| `cover` | `title` | `subtitle`, `tagline`, `accent` |
| `title` | `text` | `subtitle` |
| `heading` | `text`, `level` (1/2/3) | — |
| `paragraph` | `text` | `align` (`left`/`right`/`center`/`justify`), `style` (`body`/`lead`/`small`/`muted`) |
| `bullets` | `items: [text, ...]` | `style` (`dot`/`dash`/`check`) |
| `numbered` | `items: [text, ...]` | — |
| `callout` | `text` | `variant` (`info`/`tip`/`note`/`success`/`warning`/`danger`), `title` |
| `quote` | `text` | `attribution` |
| `banner` | `text` | `subtitle`, `color` |
| `kpi_row` | `items: [{label, value, delta?, color?}, ...]` | — |
| `card` | — | `title`, `text`, `color`, `children: [element, ...]` |
| `columns` | `columns: [[element, ...], ...]` | `gap` (points) |
| `badges` | `items: [{text, color?}, ...]` | — |
| `table` | `rows: [[cell, ...], ...]` | `header` (bool, default true), `style` (`zebra`/`minimal`/`grid`), `col_widths`, `aligns` |
| `chart` | `kind` (`bar`/`line`/`pie`), `data`, `labels` | `series_names`, `title`, `height` |
| `diagram` | `nodes: [{id, label, color?}], edges: [{from, to, label?}]` | `layout` (`horizontal`/`vertical`) |
| `timeline` | `items: [{title, text?}, ...]` | — |
| `shape` | `shape` (`rect`/`circle`/`line`/`arrow`) | `width`, `height`, `color`, `fill` |
| `image` | `path` | `width`, `height`, `caption` |
| `spacer` | — | `height` (points; default 12) |
| `hrule` | — | `color` |
| `page_break` | — | — |

### Inline markup (any text field)
- `<b>bold</b>`, `<i>italic</i>`, `<u>underline</u>`
- `<sub>...</sub>`, `<super>...</super>` (Unicode sub/super are auto-converted)
- `<br/>` for a line break
- `<font color='#rrggbb'>...</font>` for inline colour
- `<link href='https://...'>text</link>` for hyperlinks

## Returns
```
{
  ok: true,
  data: {
    output: "<absolute path>",
    page_count: <int|null>,
    size_bytes: <int>,
    element_count: <int>,
    theme: "<name>|custom",
    page_size: "letter|A4|legal"
  }
}
```

## Errors
- `invalid_input` — `output` does not end in `.pdf`, or `elements` is empty.
- `output_exists` — destination already exists and `overwrite=false`.
- `dependency_missing` — reportlab is not installed.
- `create_failed` — the PDF build raised (the message includes the cause).

## Examples

### One-pager with KPIs and a table
Call:
```
pdf.create(
  output="/tmp/inventory-summary.pdf",
  theme="professional",
  page_numbers=true,
  title="Retail Inventory Summary",
  elements=[
    {"type": "cover", "title": "Retail Inventory", "subtitle": "Q1 Summary", "tagline": "Generated from 01 Retail Inventory.xlsx"},
    {"type": "heading", "level": 1, "text": "Key figures"},
    {"type": "kpi_row", "items": [
      {"label": "Products", "value": "1,000"},
      {"label": "Categories", "value": "8"},
      {"label": "Stock value (retail)", "value": "$3.42M", "color": "#10b981"},
      {"label": "Low stock", "value": "149", "color": "#ef4444"}
    ]},
    {"type": "heading", "level": 2, "text": "Top 10 by retail value"},
    {"type": "table", "style": "zebra", "rows": [
      ["SKU", "Category", "On hand", "Retail value"],
      ["A-001", "Apparel", "320", "$48,000"],
      ["B-014", "Footwear", "210", "$41,200"]
    ]}
  ]
)
```

### Chart and diagram
Call:
```
pdf.create(
  output="/tmp/architecture.pdf",
  elements=[
    {"type": "title", "text": "System architecture"},
    {"type": "diagram", "layout": "horizontal", "nodes": [
      {"id": "u", "label": "User"},
      {"id": "a", "label": "API"},
      {"id": "d", "label": "DB"}
    ], "edges": [
      {"from": "u", "to": "a"},
      {"from": "a", "to": "d"}
    ]},
    {"type": "chart", "kind": "bar",
     "labels": ["Jan", "Feb", "Mar"],
     "data": [[120, 150, 180]],
     "series_names": ["Signups"], "title": "Quarterly signups"}
  ]
)
```

## See also
- `pdf.merge` — combine an existing cover with a body PDF.
- `pdf.see` — render the resulting PDF as page images for verification.
- `xlsx.sql` — compute the aggregates you'll put into the report before calling `pdf.create`.

</details>

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
| pages | string | no | 1-based page spec; omit to scan the document's first `max_pages` pages. |
| max_pages | int | no | Cap on the number of pages scanned for tables (default 5). Applied after the `pages` spec. When the cap drops pages, the payload includes `truncated: true` and `skipped_pages: [...]`. |

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
    ],
    // present only when truncated:
    requested_page_count: <int>,
    returned_page_count: <int>,
    skipped_pages: [<1-based>, ...],
    truncated: true,
    truncation_note: "Returned N of M requested pages..."
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
| pages | string | no | 1-based page spec, e.g. `"1"`, `"1-3"`, `"1,3-5,8"`. Omit to use the document's first `max_pages` pages. |
| preserve_layout | bool | no | If true and pdfplumber is available, preserves columns/whitespace. Default false. |
| max_pages | int | no | Cap on the number of pages returned (default 5). Applied after the `pages` spec, so asking for `"1-50"` still gives you only the first 5 unless you raise this. When the cap drops pages, the payload includes `truncated: true` and `skipped_pages: [...]`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    backend: "pdfplumber" | "pypdf",
    page_count: <int>,
    char_count: <int>,
    pages: [{page: <1-based>, text: "..."}, ...],
    // present only when truncated:
    requested_page_count: <int>,
    returned_page_count: <int>,
    skipped_pages: [<1-based>, ...],
    truncated: true,
    truncation_note: "Returned N of M requested pages..."
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
Call: `repo.scaffold_pack(name="credit_analyst", owner="team-credit-ai", description="Credit analysts drafting and reviewing corporate credit memos.", skills=["credit_memo", "xlsx_handling"], classification="internal")`
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

#### `xlsx.convert` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.convert
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, convert]
---

# xlsx.convert

## Purpose
Convert a tabular file between `.xlsx`/`.xlsm`/`.csv`/`.tsv`, optionally
extracting one sheet from a multi-sheet workbook or exploding every sheet
into its own CSV.

## When to use
- The user wants a workbook as CSV (for a downstream tool, a diff, an email).
- The user wants a CSV/TSV imported into a workbook.
- The user wants every sheet of a multi-sheet workbook as separate CSVs
  (one-file-per-sheet) — pass `explode_sheets=true`.
- The user wants to extract a single sheet of a workbook into its own
  smaller workbook.

## When NOT to use
- To change cell values — use `xlsx.edit_cells`.
- To restyle — use `xlsx.format`.
- To read the rows — use `xlsx.read` or `xlsx.sql`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Source file (`.xlsx`/`.xlsm`/`.csv`/`.tsv`). |
| output | string | yes | Destination file, or destination directory when `explode_sheets=true`. Extension picks the target format. |
| overwrite | bool | no | Replace existing output(s). Default false. |
| sheet | string | no | For xlsx → csv/tsv or xlsx → xlsx single-sheet extract: which sheet to take. Default: first. |
| explode_sheets | bool | no | If true and source is multi-sheet xlsx, write one CSV per sheet into the directory `output`. |

## Returns
Single-file conversion:
```
{ok: true, data: {output, sheet, sheet_count: 1}}
```
Explode mode:
```
{ok: true, data: {output_dir, files: [...], sheet_count: <int>}}
```

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source or output extension is not tabular.
- `sheet_not_found` — `sheet` is not in the workbook.
- `output_exists` — destination exists and `overwrite=false`.
- `invalid_input` — bad combination of `output` extension and mode.
- `dependency_missing` — openpyxl is not installed and xlsx is involved.

## Examples
### Workbook (first sheet) → CSV
Call: `xlsx.convert(path="/data/report.xlsx", output="/data/report.csv")`

### Workbook → CSV, pick the sheet
Call: `xlsx.convert(path="/data/report.xlsx", sheet="Revenue", output="/data/revenue.csv")`

### CSV → xlsx
Call: `xlsx.convert(path="/data/loans.csv", output="/data/loans.xlsx")`

### TSV → CSV
Call: `xlsx.convert(path="/data/x.tsv", output="/data/x.csv")`

### Explode every sheet into its own CSV
Call: `xlsx.convert(path="/data/report.xlsx", output="/data/report-sheets/", explode_sheets=true)`

### Extract a single sheet into a one-sheet workbook
Call: `xlsx.convert(path="/data/report.xlsx", sheet="Revenue", output="/data/revenue.xlsx")`

## See also
- `xlsx.read` — once converted, to inspect the result.
- `xlsx.write` — to assemble multi-sheet workbooks from scratch.

</details>

#### `xlsx.edit_cells` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.edit_cells
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, edit, formula]
---

# xlsx.edit_cells

## Purpose
Set the values of specific cells in an existing `.xlsx`/`.xlsm` workbook,
preserving all other cells, sheets, styles, and formulas. Write to a fresh
output path; the input is never modified in place.

## When to use
- The user wants to update a small number of cells in a workbook (assumption
  cells, totals, a status flag) without rebuilding the whole file.
- A skill needs to inject a formula (e.g. `=SUM(B2:B10)`) into an existing
  template.

## When NOT to use
- To rebuild a workbook from scratch — use `xlsx.write`.
- To apply font / fill / number formats — use `xlsx.format`.
- To recompute formula results after editing — chain `xlsx.recalc`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Source `.xlsx`/`.xlsm`. |
| output | string | yes | Destination `.xlsx`/`.xlsm`. |
| overwrite | bool | no | Replace existing output. Default false. |
| sheet | string | no | Target sheet name; defaults to the first sheet. |
| cells | list[{cell, value}] | yes | A1-notation cells and the values to assign. String values that start with `=` are written as Excel formulas. |

## Returns
```
{ok: true, data: {output, sheet, cells_written: <int>}}
```
A `warnings[]` entry will mention `xlsx.recalc` whenever a formula was
written, because openpyxl does not evaluate formulas itself.

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source is not `.xlsx`/`.xlsm`.
- `sheet_not_found` — `sheet` is not in the workbook.
- `output_exists` — destination exists and `overwrite=false`.
- `invalid_input` — empty `cells` list, missing `cell` key, or bad A1 ref.
- `write_failed` — disk or library error while saving.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Update three assumption cells
Call:
```
xlsx.edit_cells(
  path="/data/model.xlsx",
  output="/data/model-v2.xlsx",
  sheet="Assumptions",
  cells=[
    {"cell": "B2", "value": 0.05},
    {"cell": "B3", "value": 0.12},
    {"cell": "B4", "value": "Updated 2025-05"}
  ]
)
```

### Inject a SUM formula then recalc
1. `xlsx.edit_cells(path="/data/m.xlsx", output="/data/m2.xlsx", cells=[{"cell": "B11", "value": "=SUM(B2:B10)"}])`
2. `xlsx.recalc(path="/data/m2.xlsx")`

## See also
- `xlsx.write` — when you're building a brand-new workbook.
- `xlsx.format` — for styling, not values.
- `xlsx.recalc` — materialise formula results.

</details>

#### `xlsx.format` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.format
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, format, style]
---

# xlsx.format

## Purpose
Apply font, fill, alignment, number format, and column widths to a range in
an existing `.xlsx`/`.xlsm` workbook. Cell values are preserved.

## When to use
- The user asks for a header row to be bold, a column to be currency-formatted,
  zero values shown as a dash, a key assumption cell highlighted yellow, or a
  column widened.
- A skill is producing a deliverable and needs the financial-model conventions
  applied (blue inputs, black formulas, $#,##0 currency, etc.).

## When NOT to use
- To change cell *values* — use `xlsx.edit_cells`.
- To build a new workbook — use `xlsx.write`, then come back here.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Source `.xlsx`/`.xlsm`. |
| output | string | yes | Destination `.xlsx`/`.xlsm`. |
| overwrite | bool | no | Replace existing output. Default false. |
| sheet | string | no | Target sheet; defaults to the first. |
| range | string | yes | A1 range, e.g. `'A1'`, `'A1:C10'`, `'B:B'`, `'2:2'`. |
| font_name | string | no | e.g. `'Arial'`. |
| font_size | number | no | Points. |
| bold | bool | no | |
| italic | bool | no | |
| font_color | string | no | ARGB/RGB hex, e.g. `'0000FF'` (industry-standard blue for hardcoded inputs). |
| fill_color | string | no | ARGB/RGB hex, e.g. `'FFFF00'` for a yellow assumption highlight. |
| align | string | no | `'left'` \| `'center'` \| `'right'`. |
| number_format | string | no | Excel number format, e.g. `'$#,##0;($#,##0);-'`, `'0.0%'`, `'0.0x'`. |
| column_widths | object | no | `{column_letter: width}` map applied to the same sheet. |

### Financial-model colour conventions (recommended)
- Hardcoded inputs / scenario knobs: blue text `'0000FF'`.
- Formulas / calculations: black text (default).
- Cross-sheet links: green text `'008000'`.
- External-file links: red text `'FF0000'`.
- Key assumption cells: yellow fill `'FFFF00'`.

## Returns
```
{ok: true, data: {output, sheet, cells_formatted: <int>}}
```

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source is not `.xlsx`/`.xlsm`.
- `sheet_not_found` — `sheet` is not in the workbook.
- `output_exists` — destination exists and `overwrite=false`.
- `invalid_input` — missing or bad `range`.
- `write_failed` — disk or library error while saving.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Bold the header row and widen columns
Call:
```
xlsx.format(
  path="/data/m.xlsx", output="/data/m-styled.xlsx",
  range="A1:D1", bold=true, fill_color="DDDDDD",
  column_widths={"A": 20, "B": 14, "C": 14, "D": 14}
)
```

### Currency format on a column, zeros as dash
Call:
```
xlsx.format(
  path="/data/m.xlsx", output="/data/m2.xlsx",
  range="C2:C100", number_format="$#,##0;($#,##0);-"
)
```

### Highlight a key assumption
Call:
```
xlsx.format(
  path="/data/m.xlsx", output="/data/m2.xlsx",
  sheet="Assumptions", range="B2", fill_color="FFFF00", font_color="0000FF", bold=true
)
```

## See also
- `xlsx.edit_cells` — to change values, not styling.
- `xlsx.write` — initial workbook creation.

</details>

#### `xlsx.info` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.info
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, metadata]
---

# xlsx.info

## Purpose
Return the sheet inventory of a spreadsheet (name, shape, header preview)
plus workbook metadata, without dumping the actual rows.

## When to use
- The user gives you a workbook and you need to decide *which* sheet(s)
  matter before doing anything else — especially for multi-sheet `.xlsx`
  files.
- A skill needs the column names of every sheet to pick the right one or
  to compose an `xlsx.sql` query.
- The user asks "what's in this file?" — answer with the inventory before
  optionally drilling in.

## When NOT to use
- To read the actual data — use `xlsx.read` (raw rows) or `xlsx.sql`
  (computation).
- To inspect a PDF — use `pdf.read`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.xlsx`, `.xlsm`, `.csv`, or `.tsv` file. |

## Returns
```
{ok: true, data: {
  format: "xlsx" | "xlsm" | "csv" | "tsv",
  sheet_count: <int>,
  sheets: [
    {name, row_count, col_count, headers_preview: [...]},
    ...
  ],
  metadata: {title, creator, created, modified}   # xlsx/xlsm only
}}
```
`row_count` excludes the header row.

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — extension not in `.xlsx`, `.xlsm`, `.csv`, `.tsv`.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Inventory a multi-sheet workbook
Call: `xlsx.info(path="/data/q3-report.xlsx")`
Returns: `{ok: true, data: {sheet_count: 3, sheets: [{name: "Revenue", row_count: 120, col_count: 8, headers_preview: [...]}, ...]}}`

### Shape of a CSV
Call: `xlsx.info(path="/data/loans.csv")`

## See also
- `xlsx.read` — once you know which sheet you want.
- `xlsx.sql` — to compute over the sheets you discovered here.

</details>

#### `xlsx.read` &nbsp; <sub>v2 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.read
version: 2
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, tabular]
---

# xlsx.read

## Purpose
Read a spreadsheet file (`.xlsx`, `.xlsm`, `.csv`, or `.tsv`) and return its
contents as a header row + list of data rows, optionally for every sheet in
a workbook at once.

## When to use
- The user gives you a path to a spreadsheet and wants you to look at the
  actual rows (for a sample, a small dump, or a copy into your reasoning).
- A skill needs the raw cells of a workbook before deciding what to do next.
- The user wants every sheet of a multi-sheet workbook in one call —
  pass `all_sheets=true`.

## When NOT to use
- To *compute* anything (sum, average, group-by, join, filter): call
  `xlsx.sql` instead. Pulling all rows into your context just to sum them is
  wasteful and error-prone.
- To learn shape / sheet names / column previews without the data: call
  `xlsx.info` — much cheaper for large files.
- To modify a workbook: use `xlsx.write`, `xlsx.edit_cells`, `xlsx.format`.
- To read a PDF table: use `pdf.extract_tables`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the file. |
| sheet | string | no | Sheet name (xlsx only). Defaults to the first sheet. Ignored when `all_sheets=true`. |
| has_header | bool | no | If true (default), the first row becomes `headers`; otherwise it stays in `rows`. |
| all_sheets | bool | no | If true, return every sheet of the workbook under `sheets`. Xlsx only. |
| max_rows | int | no | Cap on data rows returned per sheet (default 10). When the sheet has more rows, `rows` is truncated and `truncated: true` is set in the payload. Raise it if you genuinely need more rows; use `xlsx.sql` for aggregations. |

## Returns
Single sheet:
```
{ok: true, data: {
  sheet: "<name>", sheet_names: [...],
  headers: [...] | null, rows: [[...], ...],
  row_count: <int>,            # total data rows in the sheet
  col_count: <int>,
  // present only when truncated:
  returned_row_count: <int>,   # how many rows are actually in `rows`
  truncated: true,
  truncation_note: "Showing first N of M data rows. ..."
}}
```
All sheets (`all_sheets=true`):
```
{ok: true, data: {
  sheet_names: [...],
  sheets: [{sheet, headers, rows, row_count, col_count}, ...]
}}
```
Dates / datetimes are returned as ISO-format strings.

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — extension not in `.xlsx`, `.xlsm`, `.csv`, `.tsv`.
- `sheet_not_found` — requested sheet name is not in the workbook.
- `decode_error` — CSV/TSV file is not UTF-8.
- `dependency_missing` — openpyxl is not installed.

## Examples
### Read default sheet of an xlsx
Call: `xlsx.read(path="/data/loans.xlsx")`

### Read a specific sheet
Call: `xlsx.read(path="/data/loans.xlsx", sheet="Q1")`

### Dump every sheet of a multi-sheet workbook
Call: `xlsx.read(path="/data/report.xlsx", all_sheets=true)`

### Read a CSV without treating the first row as a header
Call: `xlsx.read(path="/data/loans.csv", has_header=false)`

## See also
- `xlsx.info` — sheet inventory + shape, no row data.
- `xlsx.sql` — for anything that needs computation.
- `xlsx.convert` — to reshape between xlsx / csv / tsv.

</details>

#### `xlsx.recalc` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.recalc
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, formula, recalc]
---

# xlsx.recalc

## Purpose
Recalculate every formula in an `.xlsx`/`.xlsm` workbook (via LibreOffice
headless), materialise the resulting values, and report any residual Excel
errors (`#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, `#NAME?`, `#NUM!`, `#NULL!`).

Required after any `xlsx.write` / `xlsx.edit_cells` call that injected
formulas — openpyxl writes formula strings but does not evaluate them.

## When to use
- You injected `=SUM(...)`, `=AVERAGE(...)`, `=VLOOKUP(...)` etc. via
  `xlsx.write` or `xlsx.edit_cells` and the user needs the *values* visible
  in the workbook (e.g. so a downstream tool that reads with `data_only=true`
  sees them).
- You want a post-edit error scan to catch broken references before
  delivering the file.

## When NOT to use
- Workbooks with no formulas (CSV outputs, value-only tables) — nothing to
  recalculate.
- Performance-sensitive loops — LibreOffice startup is non-trivial.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Workbook to recalculate. |
| output | string | no | Where to write the result. Omit to overwrite the input in place. |
| overwrite | bool | no | If `output` is given and exists, allow replacing it. |
| timeout_seconds | int | no | Hard timeout for the LibreOffice call (default 60). |

## Returns
```
{ok: true, data: {
  output: "<path>",
  status: "success" | "errors_found",
  total_errors: <int>,
  error_summary: {
    "#REF!": {"count": 2, "locations": ["Sheet1!B5", "Sheet1!C10"]},
    ...
  }
}}
```

## Errors
- `file_not_found` — source path does not exist.
- `unsupported_format` — source is not `.xlsx`/`.xlsm`.
- `dependency_missing` — `soffice` (LibreOffice) is not on PATH.
- `recalc_failed` — LibreOffice exited non-zero or produced no output.
- `timeout` (retriable) — LibreOffice did not finish in time.
- `output_exists` — `output` exists and `overwrite=false`.

## Examples
### Recalculate in place
Call: `xlsx.recalc(path="/data/model.xlsx")`

### Recalculate to a separate file
Call: `xlsx.recalc(path="/data/model.xlsx", output="/data/model-final.xlsx")`

### Typical edit → recalc → verify chain
1. `xlsx.edit_cells(path="...", output="m2.xlsx", cells=[{"cell":"B11","value":"=SUM(B2:B10)"}])`
2. `xlsx.recalc(path="m2.xlsx")`
3. If `status="errors_found"`, inspect `error_summary` and fix the formulas
   with another `xlsx.edit_cells` round.

## See also
- `xlsx.write`, `xlsx.edit_cells` — produce the formulas this recalculates.
- `xlsx.read` — read the values back after recalc.

</details>

#### `xlsx.sql` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.sql
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, query, sql]
---

# xlsx.sql

## Purpose
Run a read-only SQL query over one or more spreadsheet files. Each input is
loaded into an in-memory SQLite database; every `.xlsx` sheet becomes its own
table. Use this whenever the user wants computation (sum, average, group-by,
join, filter, top-N, distinct) — never reimplement that in your head.

## When to use
- The user asks a question that requires aggregation, filtering, joining,
  sorting, or grouping over tabular data — even on a single sheet.
- The data is large enough that dumping rows via `xlsx.read` and computing in
  your head would be slow, wasteful, or unreliable.
- You need to join two files (e.g. a CSV against a sheet from a workbook).

## When NOT to use
- To dump the raw rows for a few-line preview — `xlsx.read` is simpler.
- To inspect schema / sheet names — use `xlsx.info` first, then craft the SQL.
- To *modify* a workbook — this tool is read-only. Use `xlsx.write` or
  `xlsx.edit_cells`.
- To read a PDF table — use `pdf.extract_tables`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| inputs | list | yes | Each entry is either a path string or `{path, alias?, sheet?}`. `.xlsx` files load every sheet as a separate table; pass `sheet=...` to restrict, or `alias=...` to rename the table. |
| query | string | yes | A single read-only SQL statement (`SELECT`, `WITH`, or `VALUES`). SQLite dialect. No semicolons, no DDL/DML. |
| max_rows | int | no | Cap on returned rows (default 1000). |

### Table naming rules
- A CSV/TSV named `loans.csv` becomes table `loans`. Pass `alias` to rename.
- A workbook `report.xlsx` with sheets `Revenue`, `Costs` becomes tables
  `Revenue`, `Costs`. Pass `sheet="Revenue"` to load just one. With multiple
  files that share sheet names, pass `alias` to disambiguate (e.g.
  `alias="q1"` → tables become `q1_Revenue`, `q1_Costs`).
- Non-identifier characters in sheet names are replaced with `_`; the original
  name is returned in `data.tables`.
- The first row of each sheet/file is used as column names (sanitised the
  same way). Quote identifiers with double quotes if they contain odd
  characters: `SELECT "Net Revenue" FROM Revenue`.

### Type handling
- Values are inserted as their native Python types (text / number / null).
  Use `CAST("col" AS REAL)` if a column read as text needs arithmetic.

## Returns
```
{ok: true, data: {
  columns: ["col_a", "col_b", ...],
  rows: [[...], ...],
  row_count: <int>,
  truncated: <bool>,
  tables: {"<sqlite-table>": {"path": "...", "sheet": "..."}, ...}
}}
```

## Errors
- `file_not_found` — one of the input paths does not exist.
- `unsupported_format` — an input extension is not tabular.
- `sheet_not_found` — `sheet` filter does not match any sheet in the workbook.
- `invalid_input` — empty query, multiple statements, or no inputs.
- `forbidden_statement` — query is not `SELECT`/`WITH`/`VALUES`, or mentions a
  write keyword.
- `sql_error` — SQLite rejected the query (syntax error, unknown table, etc.).
- `dependency_missing` — openpyxl is not installed and an xlsx input was given.

## Examples
### Sum a column on a single CSV
Call:
```
xlsx.sql(
  inputs=["/data/loans.csv"],
  query="SELECT SUM(amount) AS total FROM loans"
)
```

### Aggregate across one sheet of a workbook
Call:
```
xlsx.sql(
  inputs=[{"path": "/data/report.xlsx", "sheet": "Revenue", "alias": "rev"}],
  query="SELECT region, SUM(net) AS net FROM rev GROUP BY region ORDER BY net DESC"
)
```

### Join two files
Call:
```
xlsx.sql(
  inputs=[
    {"path": "/data/customers.csv"},
    {"path": "/data/orders.xlsx", "sheet": "2024"}
  ],
  query="SELECT c.name, SUM(o.amount) AS spend FROM customers c JOIN \"2024\" o ON o.customer_id = c.id GROUP BY c.name"
)
```

### Join every sheet of a multi-sheet workbook
Call:
```
xlsx.sql(
  inputs=[{"path": "/data/quarterly.xlsx", "alias": "q"}],
  query="SELECT 'Q1' AS quarter, SUM(amount) FROM q_Q1 UNION ALL SELECT 'Q2', SUM(amount) FROM q_Q2"
)
```

## See also
- `xlsx.info` — discover sheet and column names before writing SQL.
- `xlsx.read` — when you need raw rows, not a computed answer.

</details>

#### `xlsx.write` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: xlsx.write
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, write, create]
---

# xlsx.write

## Purpose
Create a brand-new spreadsheet from in-memory rows. Supports `.xlsx`/`.xlsm`
(single- or multi-sheet) and `.csv`/`.tsv` (single-sheet only). Never
modifies an existing workbook in place — see `xlsx.edit_cells` for that.

## When to use
- The user asks you to produce a fresh spreadsheet from data you have already
  computed or extracted.
- A skill needs to materialise a multi-sheet workbook (e.g. one sheet per
  region) in one call.

## When NOT to use
- To edit specific cells of an existing workbook (preserving everything else)
  — use `xlsx.edit_cells`.
- To restyle existing cells — use `xlsx.format`.
- To convert between formats — use `xlsx.convert`.
- To write computed values from formulas — write the formula via
  `xlsx.edit_cells` (or as a string here) and then run `xlsx.recalc`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| output | string | yes | Destination path. Extension picks the format. |
| overwrite | bool | no | Replace existing file. Default false. |
| sheets | object | no* | Multi-sheet form: `{sheet_name: {headers?, rows}}`. xlsx only. |
| sheet_name | string | no* | Single-sheet form: name of the sheet (default 'Sheet1'). |
| headers | list | no* | Single-sheet form: header row. |
| rows | list[list] | no* | Single-sheet form: data rows. |

\* Provide either `sheets` (multi-sheet) **or** `sheet_name`/`headers`/`rows`
(single-sheet). Mixing both is undefined.

### Formula cells
A string value beginning with `=` (e.g. `"=SUM(A2:A10)"`) is written as an
Excel formula. The cell's *value* is not materialised until you run
`xlsx.recalc`. CSV/TSV outputs treat such strings literally.

## Returns
```
{ok: true, data: {output, sheet_names: [...], sheet_count: <int>}}
```

## Errors
- `invalid_input` — neither `sheets` nor `headers`/`rows` was provided; or a
  malformed sheet spec; or CSV requested with multiple sheets.
- `unsupported_format` — output extension is not tabular.
- `output_exists` — file exists and `overwrite=false`.
- `write_failed` — disk or library error while saving.
- `dependency_missing` — openpyxl is not installed (xlsx output).

## Examples
### Single-sheet xlsx
Call:
```
xlsx.write(
  output="/tmp/loans.xlsx",
  sheet_name="Loans",
  headers=["id", "amount"],
  rows=[["L1", 100], ["L2", 250]]
)
```

### Multi-sheet workbook
Call:
```
xlsx.write(
  output="/tmp/quarterly.xlsx",
  sheets={
    "Q1": {"headers": ["region","net"], "rows": [["EMEA", 12], ["NA", 18]]},
    "Q2": {"headers": ["region","net"], "rows": [["EMEA", 14], ["NA", 22]]}
  }
)
```

### CSV output
Call: `xlsx.write(output="/tmp/loans.csv", headers=["id","amount"], rows=[["L1",100]])`

### A sheet with totals as formulas (then recalc)
1. `xlsx.write(output="/tmp/m.xlsx", sheet_name="M", headers=["amt"], rows=[[10],[20],[30],["=SUM(A2:A4)"]])`
2. `xlsx.recalc(path="/tmp/m.xlsx")`

## See also
- `xlsx.edit_cells` — modify cells in an existing workbook.
- `xlsx.format` — apply font / fill / number format after writing.
- `xlsx.recalc` — materialise formula results.
- `xlsx.convert` — same data shape, different format.

</details>

## By tag

- **catalog** — `repo.read_catalog`, `repo.search_catalog`
- **combine** — `pdf.merge`
- **convert** — `xlsx.convert`
- **create** — `pdf.create`, `xlsx.write`
- **dedup** — `repo.search_catalog`
- **deterministic** — `text.extract_lines`, `text.word_count`
- **diagnostic** — `core.echo`
- **docs** — `repo.read_doc`
- **docstore** — `docstore.fetch`
- **edit** — `xlsx.edit_cells`
- **extract** — `text.extract_lines`
- **fetch** — `docstore.fetch`
- **format** — `xlsx.format`
- **forms** — `pdf.fill_form`, `pdf.form_fields`
- **formula** — `xlsx.edit_cells`, `xlsx.recalc`
- **internal-docs** — `docstore.fetch`
- **meta** — `orchestrator.delegate`
- **metadata** — `pdf.read`, `xlsx.info`
- **metrics** — `text.word_count`
- **numeric** — `text.extract_lines`
- **ocr** — `pdf.ocr`
- **pack-authoring** — `repo.scaffold_pack`
- **pdf** — `pdf.create`, `pdf.decrypt`, `pdf.encrypt`, `pdf.extract_tables`, `pdf.extract_text`, `pdf.fill_form`, `pdf.form_fields`, `pdf.merge`, `pdf.ocr`, `pdf.read`, `pdf.rotate`, `pdf.see`, `pdf.split`
- **query** — `xlsx.sql`
- **read** — `docstore.fetch`, `pdf.extract_tables`, `pdf.extract_text`, `pdf.form_fields`, `pdf.ocr`, `pdf.read`, `pdf.see`, `repo.read_catalog`, `repo.read_doc`, `xlsx.info`, `xlsx.read`, `xlsx.sql`
- **recalc** — `xlsx.recalc`
- **reference** — `repo.read_catalog`, `repo.read_doc`
- **report** — `pdf.create`
- **routing** — `orchestrator.delegate`
- **scaffold** — `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`
- **search** — `repo.search_catalog`
- **security** — `pdf.decrypt`, `pdf.encrypt`
- **skill-authoring** — `repo.scaffold_skill`
- **smoke-test** — `core.echo`
- **split** — `pdf.split`
- **spreadsheet** — `xlsx.convert`, `xlsx.edit_cells`, `xlsx.format`, `xlsx.info`, `xlsx.read`, `xlsx.recalc`, `xlsx.sql`, `xlsx.write`
- **sql** — `xlsx.sql`
- **style** — `xlsx.format`
- **tabular** — `pdf.extract_tables`, `xlsx.read`
- **text** — `pdf.extract_text`, `text.extract_lines`, `text.word_count`
- **tool-authoring** — `repo.scaffold_tool`
- **transform** — `pdf.rotate`
- **vision** — `pdf.see`
- **write** — `pdf.create`, `pdf.decrypt`, `pdf.encrypt`, `pdf.fill_form`, `pdf.merge`, `pdf.rotate`, `pdf.split`, `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`, `xlsx.convert`, `xlsx.edit_cells`, `xlsx.format`, `xlsx.recalc`, `xlsx.write`
