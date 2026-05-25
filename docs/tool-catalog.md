# Tool catalog

Generated from the live tool registry. Do not edit by hand.
Re-render with `python scripts/check_catalog.py --write`.

**46 tools** across **9 domains**.

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

### `html`

#### `html.create` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: html.create
version: 1
owner: team-doc-ai
classification: [internal]
tags: [html, write, create, report]
---

# html.create

## Purpose
Author a **single-file, dependency-free, print-ready** HTML report from
a structured list of elements. The output:

- ships as one `.html` file with **inline CSS**, **inline SVG charts**,
  **base64-embedded images**, **system fonts**, and **no network calls** —
  works offline forever (the "single-file rule" from Anthropic's
  HTML-as-default guidance, May 2026);
- includes a `@media print` block so `Ctrl+P` (or `html.to_pdf`)
  produces a clean A4 PDF with hidden chrome, repeated table headers,
  and proper page-break-avoidance on cards and rows;
- is **WCAG-aware**: semantic headings, focus-visible outlines, ≥ 4.5:1
  contrast on every theme, descriptive `alt` text required on images.

Prefer this over hand-rolling HTML or writing Python templates: it bakes
in the visual conventions (cover, KPIs, callouts, SVG charts, timelines,
collapsibles, page-printable layout) and produces reports that look
authored rather than templated.

## When to use
- The user (or supervisor) decides the output should be a **report** —
  a status update, audit, analysis writeup, research summary, decision
  doc, weekly report, project plan, or any other multi-section
  deliverable — and did not explicitly ask for `.pdf`, `.pptx`,
  `.xlsx`, or `.docx`.
- A skill needs to materialise structured findings (KPIs, tables,
  bullets, narrative) as a shareable artifact.

## When NOT to use
- The user asked for a specific other format — use `pdf.create`,
  `pptx.create`, or `xlsx.write` instead.
- The output is a one-paragraph reply, a code snippet, a small table,
  or a chat answer — just answer in plain text.
- The output is meant to be edited collaboratively in Git — Markdown is
  better for that.

## Parameters
| name | type | required | description |
|---|---|---|---|
| output | string | yes | Destination `.html` / `.htm` path. Parent dirs are created. |
| elements | object[] | yes | Ordered element list (see below). |
| title | string | no | Document `<title>`. |
| theme | string \| object | no | Theme name or custom palette. Default `"professional"`. |
| header | string \| object | no | Optional on-screen page header. Hidden when printing. |
| footer | string \| object | no | Optional on-screen page footer. Hidden when printing. |
| max_width | int | no | Max content width in pixels for the on-screen layout. Default 920. |
| author | string | no | Document metadata: author. |
| subject | string | no | Document metadata: subject / description. |
| overwrite | bool | no | If true, replace the output file if it already exists. |

## Themes
`default`, `professional`, `modern`, `minimal`, `vibrant`, `dark`, or
a custom palette object with the following keys (all hex strings):
`primary`, `secondary`, `accent`, `text`, `muted`, `surface`, `border`,
`background`, `success`, `warning`, `danger`, `info`. Missing keys
inherit from the `default` theme.

## Element types
Every element is `{"type": "<name>", ...fields}`.

| type | required fields | notes |
|---|---|---|
| `cover` | `title` | `subtitle`, `tagline`. Use exactly once at the top. |
| `title` | `text` | `subtitle`. Lighter than `cover`; use for sub-pages. |
| `heading` | `text` | `level` 1-4 (default 2), optional `id` for TOC anchors. |
| `paragraph` | `text` | `style`: `lead`/`muted`/`small`; `align`. |
| `bullets` | `items: [str]` | Inline markup allowed in items. |
| `numbered` | `items: [str]` | Same. |
| `callout` | `text` | `variant`: `info`/`tip`/`note`/`success`/`warning`/`danger`; `title`. |
| `quote` | `text` | `attribution`. |
| `banner` | `text` (or `title`) | `subtitle`. Full-width tinted block. |
| `kpi_row` | `items: [{label, value, delta?, direction?}]` | 2-6 cards. `direction`: `up`/`down` for delta colour. |
| `card` | — | `title`, `text`, `children: [element, ...]`. |
| `columns` | `columns: [[element, ...], ...]` | 2-4 columns of nested elements. |
| `badges` | `items: [str \| {text, color?}]` | Pill tags. |
| `table` | `rows: [[cell, ...], ...]` | `header` (bool, default true), `caption`, `aligns`. |
| `chart` | `kind`, `labels`, `data` | `kind`: `bar`/`line`/`pie`. `series_names`. Pure inline SVG. |
| `timeline` | `items: [{when?, title?, text?}]` | Vertical bullet timeline. |
| `hrule` | — | Horizontal rule. |
| `spacer` | — | `height` in px (default 12). |
| `image` | `path`, `alt` | `caption`, `width`. Embedded as base64. `alt` is required (pass `"decorative"` for purely decorative imagery). |
| `raw_html` | `html` | Escape-hatch for advanced HTML. Trust boundary: do not pass untrusted input. |
| `page_break` | — | Forces a print page break (no effect on screen). |
| `toc` | `items: [str \| {text, href}]` | `title`. Use with `heading` `id` anchors. |
| `details` | `summary` | `text`, `children`, `open` (bool). Collapsible. |

Inline markup in any text field: `<b>`, `<i>`, `<u>`, `<code>`, `<br>`,
`<a href="...">`. Anything else is HTML-escaped.

## Returns
```
{
  ok: true,
  data: {
    output: "<absolute path>",
    size_bytes: <int>,
    theme: "<name>|custom",
    elements_rendered: ["cover", "kpi_row", ...],
    element_count: <int>,
    self_contained: true
  }
}
```

## Errors
- `invalid_input` — `output` doesn't end in `.html` / `.htm`, or `elements` is empty.
- `output_exists` — destination exists and `overwrite=false`.
- `create_failed` — a renderer raised. The message includes the element index and type.

## Examples
### Weekly status report
Call:
```
html.create(
  output="/tmp/status-2026-05-24.html",
  title="Project Lighthouse — Weekly Status",
  theme="professional",
  header={"left": "Project Lighthouse", "right": "Week 21 · 2026"},
  footer={"center": "Confidential — internal"},
  elements=[
    {"type": "cover", "title": "Weekly Status",
     "subtitle": "Project Lighthouse · Week 21, 2026",
     "tagline": "Prepared by the platform team"},
    {"type": "toc", "items": [
      {"text": "Headline numbers", "href": "kpis"},
      {"text": "What shipped", "href": "shipped"},
      {"text": "Risks", "href": "risks"},
      {"text": "Next week", "href": "next"}
    ]},
    {"type": "heading", "level": 2, "id": "kpis", "text": "Headline numbers"},
    {"type": "kpi_row", "items": [
      {"label": "Active users", "value": "12,430", "delta": "+8.2% WoW", "direction": "up"},
      {"label": "P99 latency",  "value": "184 ms",  "delta": "-12 ms",   "direction": "up"},
      {"label": "Error rate",   "value": "0.21%",   "delta": "+0.04 pp", "direction": "down"},
      {"label": "Open bugs",    "value": "17"}
    ]},
    {"type": "chart", "kind": "line",
     "title": "Daily active users — last 14 days",
     "labels": ["M","T","W","T","F","S","S","M","T","W","T","F","S","S"],
     "data": [[9120, 9410, 9550, 9610, 9700, 7800, 7920, 9800, 10100, 10250, 10400, 10560, 8900, 9050]],
     "series_names": ["DAU"]},
    {"type": "heading", "level": 2, "id": "shipped", "text": "What shipped"},
    {"type": "bullets", "items": [
       "Audit-log export endpoint (closes <code>#PL-412</code>)",
       "SSO retry-with-fresh-token flow",
       "Dashboard empty-state copy refresh"
    ]},
    {"type": "heading", "level": 2, "id": "risks", "text": "Risks"},
    {"type": "callout", "variant": "warning", "title": "EU launch dependency",
     "text": "Vendor contract still in legal review; blocks the Jun 3 cut-off."},
    {"type": "heading", "level": 2, "id": "next", "text": "Next week"},
    {"type": "timeline", "items": [
      {"when": "Mon", "title": "Ship rate-limit config UI"},
      {"when": "Wed", "title": "Decision review: data residency"},
      {"when": "Fri", "title": "Cut release candidate"}
    ]}
  ]
)
```

### Compact audit report
Call:
```
html.create(
  output="/tmp/audit.html",
  title="Q4 access audit",
  theme="minimal",
  elements=[
    {"type": "title", "text": "Q4 access audit",
     "subtitle": "Conducted 2026-05-24"},
    {"type": "callout", "variant": "success",
     "title": "Overall result",
     "text": "No critical findings. Two informational items follow."},
    {"type": "table", "header": true,
     "rows": [
       ["#", "Finding", "Severity", "Status"],
       ["1", "Stale service account in <code>billing-prod</code>", "Info", "Removed"],
       ["2", "Two admins missing MFA enrolment date", "Info", "Confirmed enrolled"]
     ],
     "aligns": ["right", "left", "center", "center"]}
  ]
)
```

## See also
- `html.see` — render the resulting report as page images for visual
  QA. **Always do this once and look for the issues listed in the
  `html_reporting` skill QA checklist.**
- `html.to_pdf` — export the same HTML to a PDF.
- `pdf.create` — when the user explicitly asked for PDF.
- `pptx.create` — when the user explicitly asked for a slide deck.

</details>

#### `html.extract_text` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: html.extract_text
version: 1
owner: team-doc-ai
classification: [internal]
tags: [html, read, text]
---

# html.extract_text

## Purpose
Extract the readable text content of an HTML file. Strips `<script>`,
`<style>`, and template/noscript blocks; preserves block-level
structure with line breaks; collapses whitespace. Image `alt` text is
rendered inline as `[image: <alt>]` so it isn't lost.

## When to use
- The user asks "what does this HTML say" / "summarise this page".
- A skill needs the body text to feed into summarisation, translation,
  or comparison.
- You want to re-flow an HTML report's content into a different format
  (e.g. an email).

## When NOT to use
- For element counts or metadata — use `html.read` (cheaper).
- For visual layout, charts, or rendered styles — use `html.see`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.html` / `.htm` file. |
| max_chars | int | no | Cap on returned text. Result is truncated and `truncated=true` set when hit. Default 50000. Pass 0 to disable. |

## Returns
```
{
  ok: true,
  data: {
    title: <str|null>,
    text: <str>,
    char_count: <int>,
    truncated: <bool>
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `parse_failed` — HTML parse error.

## Examples
### Full body
Call: `html.extract_text(path="/tmp/audit.html")`

### Quick first page
Call: `html.extract_text(path="/tmp/long-report.html", max_chars=4000)`

## See also
- `html.read` — title and counts only.
- `html.see` — image render when layout matters.

</details>

#### `html.read` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: html.read
version: 1
owner: team-doc-ai
classification: [internal]
tags: [html, read, metadata]
---

# html.read

## Purpose
Open an HTML file and return its `<title>`, byte size, element counts
(headings, paragraphs, tables, images, links, `<script>`, `<style>`),
and whether it is **self-contained** (no remote stylesheets, scripts, or
images). Use this first to size up an HTML document before extracting
or rendering it.

## When to use
- The user hands you a `.html` / `.htm` path and asks "what is this".
- You produced an HTML report via `html.create` and want to confirm the
  output is single-file and dependency-free before sharing it.
- A skill needs the title or section counts to drive a follow-up call.

## When NOT to use
- For the readable body text — use `html.extract_text`.
- To rasterise pages for visual inspection — use `html.see`.
- To convert to PDF — use `html.to_pdf`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.html` or `.htm` file. |

## Returns
```
{
  ok: true,
  data: {
    path: "<resolved>",
    title: <str|null>,
    size_bytes: <int>,
    self_contained: <bool>,    // true ⇒ no external stylesheets/scripts/img URLs
    counts: { headings, paragraphs, tables, images, links, scripts, styles }
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file does not have a `.html` / `.htm` extension or could not be decoded.
- `parse_failed` — the HTML parser raised; the message includes the cause.

## Examples
### Inspect a report
Call: `html.read(path="/tmp/q4-status.html")`

## See also
- `html.extract_text` — readable body text.
- `html.see` — render pages as images for visual QA.
- `html.to_pdf` — export to a print-quality PDF.

</details>

#### `html.see` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: html.see
version: 1
owner: team-doc-ai
classification: [internal]
tags: [html, read, vision]
---

# html.see

## Purpose
Rasterise up to 5 pages of an HTML file and inject them into the
conversation as images, so the model can *look* at the report rather
than only parse its text. Mirrors `pdf.see` / `pptx.see` for HTML files:
under the hood the file is converted to PDF once (`soffice --convert-to
pdf`), then the selected pages are rendered with `pypdfium2`.

The page numbers refer to the **print pagination** of the document
(the same paginator that `@media print` uses). For reports authored
with `html.create`, that gives stable per-page screenshots that match
what the user would see in a printed copy.

## When to use
- Verifying your own output after `html.create`. **Always do this once
  and look for layout issues (see the html_reporting skill QA checklist).**
- The user asks "show me what page 2 looks like" or "is this readable?".
- You suspect the HTML mis-renders (overflowing tables, broken charts).

## When NOT to use
- For the readable text — `html.extract_text` is far cheaper.
- To process many pages at once — this tool refuses more than 5 pages
  per call (`too_many_pages`).

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.html` / `.htm` file. |
| pages | string | no | 1-based page spec; max 5, e.g. `"1"`, `"2-4"`, `"1,3,5"`. Omit to render page 1 only. |
| scale | float | no | Render scale; `2.0` ≈ 200dpi. Keep ≤ `3.0`. Default `2.0`. |
| timeout_seconds | int | no | LibreOffice subprocess hard limit (default 120). |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved>",
    page_count: <int>,                     // total pages in the printed pagination
    rendered: [{ page: <1-based>, bytes: <b64 length> }, ...],
    scale: <float>
  },
  images: [ToolImage, ...]                  // attached to the next turn as multimodal content
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdfium2` is not installed, or `soffice` is not on `PATH`.
- `page_out_of_range` / `invalid_input` — bad `pages` spec.
- `too_many_pages` — more than 5 pages requested in a single call.
- `timeout` / `convert_failed` — LibreOffice failed.
- `render_failed` — `pypdfium2` raised on a specific page.

## Examples
### See page 1 (the default)
Call: `html.see(path="/tmp/report.html")`

### See pages 2-4
Call: `html.see(path="/tmp/report.html", pages="2-4")`

### See three scattered pages
Call: `html.see(path="/tmp/long.html", pages="1,3,5")`

## See also
- `html.create` — author the HTML in the first place.
- `html.extract_text` — cheap text-only inspection.
- `html.to_pdf` — keep the PDF instead of just page images.

</details>

#### `html.to_pdf` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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
version: 3
owner: team-doc-ai
classification: [internal]
tags: [pdf, write, create, report]
---

# pdf.create

## Purpose
Render a complete HTML document to PDF in **one tool call**. You write
the HTML (and CSS), `pdf.create` puts it on paper. The tool does **not**
wrap fragments, inject a theme, override your `@page` rule, or force any
print colours — what you write is what gets rendered.

The renderer is **WeasyPrint** (fallback: **LibreOffice headless** when
WeasyPrint's native libs are missing). WeasyPrint implements CSS Paged
Media, so the full design vocabulary of a modern browser is available
*plus* paged-media features browsers don't expose. See "Design surface"
below.

## When to use
- The user wants a PDF deliverable: report, summary, one-pager, memo,
  proposal, brochure, certificate, invoice, dashboard print-out, etc.
- You have structured data (from `xlsx.sql`, `pdf.extract_text`, etc.)
  and want to present it as a polished, paginated document.
- You authored an HTML report with `html.create` and now want a
  printable PDF copy of the same content — pass that file's path here.

## When NOT to use
- Slide deck → use `pptx.create`.
- Web-shareable artefact → use `html.create` (skip the PDF step).
- Fillable PDF form → use `pdf.fill_form` on an existing template.
- The user wants Word output → use `docx.create`.

## Parameters

You must provide:

- `output` — destination `.pdf` path. Parent dirs are created.
- `html` — **either** a complete HTML document as a string, **or** an
  absolute path to a `.html` / `.htm` file on disk.

Anything ≤ 1 KB, single-line, ending in `.html`/`.htm` is treated as a
path. Everything else is treated as raw HTML. Raw HTML **must** start
with `<!doctype html>` and contain an `<html>` element — fragments are
rejected, on purpose, because fragments can't declare an `@page` rule.

Optional:

- `title`, `author`, `subject` — PDF metadata (search indexers see
  these). If omitted, WeasyPrint picks up `<title>` from the HTML.
- `engine` — `auto` (default) | `weasyprint` | `libreoffice`.
- `timeout_seconds` — kill switch for the LibreOffice subprocess.
- `overwrite` — replace an existing output file.

## Returns

```jsonc
{
  ok: true,
  data: {
    output:     "<path>",
    size_bytes: <int>,
    page_count: <int>,
    engine:     "weasyprint" | "libreoffice",
    warnings:   [<string>, ...]    // e.g. fallback notes
  }
}
```

## Errors

- `invalid_input` — `output` is not a `.pdf` path, `html` is missing/empty,
  the supplied `.html` file doesn't exist, or a raw-HTML string isn't a
  complete document (no `<!doctype html>` / `<html>` tag).
- `output_exists` — destination file exists and `overwrite=false`.
- `dependency_missing` — both engines unavailable. Usually WeasyPrint's
  native libs (Pango/Cairo) missing; the message names the install
  command for mac/debian.
- `create_failed` — engine-level failure (catch-all). The message
  includes the underlying cause.

## Design surface

You have the full design freedom of a modern browser plus the
paged-media extensions. The features below are the ones that *survive
print* — the ones agents most commonly under-use.

### Page geometry — set whatever you want
```html
<style>
  @page { size: A4; margin: 18mm; }                  /* A4 portrait     */
  @page { size: A4 landscape; margin: 12mm; }        /* landscape       */
  @page { size: letter; margin: 0.75in; }            /* US letter       */
  @page { size: 297mm 420mm; margin: 0; }            /* A3, full bleed  */
  @page { size: 1080px 1920px; margin: 0; }          /* social-story    */
  @page { size: 5.5in 8.5in; margin: 14mm 16mm; }    /* half-letter     */
</style>
```

### Named pages — different geometry per section
```html
<style>
  @page cover    { size: A4; margin: 0; }
  @page content  { size: A4; margin: 22mm 18mm 26mm 18mm;
                   @bottom-right { content: counter(page) " / " counter(pages); } }
  .cover  { page: cover;  }
  .body   { page: content; }
  .body   { break-before: page; }    /* start content on a fresh page */
</style>
```

### Running headers & footers, page counters
```css
@page {
  @top-left     { content: "Q4 Inventory Report"; font: 9pt sans-serif; color: #6b7280; }
  @top-right    { content: string(section);       font: 9pt sans-serif; color: #6b7280; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 9pt sans-serif; }
}
h2 { string-set: section content(); }   /* live "current section" feed */
```

The 16 margin boxes (`@top-left-corner`, `@top-left`, `@top-center`,
`@top-right`, `@top-right-corner`, and the matching `@bottom-*`,
`@left-*`, `@right-*`) are all available. Use `:left` / `:right` /
`:first` page pseudo-selectors for mirrored or chapter-opening pages.

### Page-break control
```css
.kpi-grid, .card  { break-inside: avoid; }     /* never split a card    */
h2                { break-before: page; }      /* each section new page */
table             { break-inside: auto; }
thead             { display: table-header-group; }  /* repeat on each page */
tfoot             { display: table-footer-group; }
```

### Fonts — embedded subsets, web fonts
```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap">
<style>
  body { font-family: 'Inter', system-ui, sans-serif; }

  /* Or self-host: */
  @font-face {
    font-family: 'Suisse';
    src: url('https://your.cdn/SuisseIntl.woff2') format('woff2');
    font-weight: 400 700;
  }
</style>
```

Fonts are subset-embedded, so the PDF stays small and looks identical
on any reader.

### Full bleed, backgrounds, gradients, shadows
```css
@page { size: A4; margin: 0; }
.cover {
  width: 210mm; height: 297mm;
  background: linear-gradient(135deg, #0f172a 0%, #4338ca 100%);
  color: white;
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: 28mm 22mm;
}
.cover h1 { font-size: 56pt; letter-spacing: -0.02em; }
```

### Modern layout — Grid & Flex
```css
.kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12mm;
}
.kpi      { background: #f8fafc; border-radius: 6mm; padding: 8mm; }
.kpi .v   { font-size: 28pt; font-weight: 700; color: #0f172a; }
.kpi .d   { color: #16a34a; font-size: 10pt; }
```

### Two-column body text
```css
.body-prose { column-count: 2; column-gap: 8mm; column-rule: 1px solid #e5e7eb; }
```

### Internal links & TOC
```html
<a href="#findings">Jump to findings →</a>
<h2 id="findings">Findings</h2>
```
WeasyPrint emits a clickable PDF link plus an entry in the bookmark
tree (use `<h1>`/`<h2>` ordering — bookmarks are auto-generated).

### SVG, images, charts
SVG embeds as vectors (sharp at any zoom). Inline charts produced by
any JS-free path (vega-lite render, matplotlib → SVG, server-side
Chart.js → SVG) drop straight in. Raster images are subset to the
output DPI.

## Pattern: lean on `html.create` for the skeleton
When you need a structured report but want full design control, the
fastest path is:

1. Use `html.create(elements=[…], path="/tmp/draft.html")` to get a
   themed, well-structured HTML report on disk.
2. Open it (read it back), tweak the `<style>` block / add your `@page`
   rules, save under a new path.
3. Call `pdf.create(html="/tmp/final.html", output="…")`.

This gives you `html.create`'s charts, tables, KPI rows, callouts, etc.
*and* unrestricted design control.

## Examples

### Minimal — a memo
```
pdf.create(
  output="/tmp/memo.pdf",
  html="""<!doctype html><html><head><meta charset="utf-8">
    <title>Field Memo</title>
    <style>
      @page { size: A4; margin: 22mm;
              @bottom-right { content: counter(page); font: 9pt sans-serif; color: #6b7280; } }
      body  { font: 11pt/1.55 'Helvetica Neue', sans-serif; color: #111827; }
      h1    { font-size: 22pt; margin: 0 0 6mm; color: #0f172a; }
      .meta { color: #6b7280; font-size: 9.5pt; margin-bottom: 10mm; }
    </style></head><body>
    <h1>Field memo — Q4 inventory</h1>
    <p class="meta">2026-01-08 · CIB Gen-AI</p>
    <p>Stock cover dropped 14% in November on the back of …</p>
  </body></html>"""
)
```

### Full-bleed cover + paginated body
```
pdf.create(
  output="/tmp/report.pdf",
  title="Retail Inventory Report",
  author="CIB Gen-AI",
  html="""<!doctype html><html><head><meta charset="utf-8">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap">
    <style>
      @page cover   { size: A4; margin: 0; }
      @page content { size: A4; margin: 22mm 18mm 28mm 18mm;
                      @top-left  { content: "Retail Inventory Report"; font: 9pt 'Inter'; color: #6b7280; }
                      @bottom-right { content: counter(page) " / " counter(pages); font: 9pt 'Inter'; color: #6b7280; } }
      body { font: 10.5pt/1.55 'Inter', sans-serif; color: #111827; margin: 0; }
      .cover { page: cover;
               width: 210mm; height: 297mm;
               background: radial-gradient(circle at 20% 0%, #312e81, #0f172a 70%);
               color: white; padding: 32mm 24mm; box-sizing: border-box;
               display: flex; flex-direction: column; justify-content: flex-end; }
      .cover h1 { font-size: 56pt; font-weight: 800; letter-spacing: -0.02em; margin: 0; }
      .cover p  { font-size: 14pt; opacity: 0.8; }
      .body  { page: content; break-before: page; }
      h2     { font-size: 18pt; margin: 14mm 0 4mm; color: #0f172a; }
      .kpis  { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6mm; }
      .kpi   { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 4mm;
               padding: 6mm; break-inside: avoid; }
      .kpi .v { font-size: 24pt; font-weight: 700; }
      .kpi .l { color: #6b7280; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.04em; }
    </style></head><body>
    <section class="cover">
      <h1>Retail Inventory</h1><p>Q4 2025 · CIB Gen-AI</p>
    </section>
    <section class="body">
      <h2>At a glance</h2>
      <div class="kpis">
        <div class="kpi"><div class="l">SKUs</div><div class="v">1,042</div></div>
        <div class="kpi"><div class="l">Categories</div><div class="v">8</div></div>
        <div class="kpi"><div class="l">On-hand $</div><div class="v">$4.2M</div></div>
        <div class="kpi"><div class="l">Stockouts</div><div class="v">37</div></div>
      </div>
    </section>
  </body></html>"""
)
```

### Convert an `html.create` report to PDF
```
pdf.create(
  output="/tmp/q4-status.pdf",
  html="/tmp/q4-status.html"
)
```

## See also
- `html.create` — author the same content as a self-contained HTML
  report (good starting point — pipe its output here for the PDF).
- `xlsx.sql` — compute aggregates *before* you compose the HTML.
- `pdf.see` — visual QA on the resulting PDF (max 5 pages per call).
- `pdf.extract_text`, `pdf.merge`, `pdf.split`, `pdf.encrypt` — operate
  on the produced PDF further.

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

### `pptx`

#### `pptx.convert` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

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

</details>

#### `pptx.create` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.create
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, create, deck]
---

# pptx.create

## Purpose
Author a brand-new PowerPoint deck from a structured list of slide
objects. Each slide picks one of a small set of opinionated layouts
(`cover`, `title`, `section`, `content`, `two_column`, `kpi`, `table`,
`chart`, `image`, `image_text`, `quote`, `conclusion`) and the engine
draws it with the chosen theme — covers + closers get a full-bleed
primary background, content slides get a clean title bar, KPI rows get
flat cards, charts use native PowerPoint chart objects, and so on.

Pick a theme (`default`, `professional`, `modern`, `minimal`,
`vibrant`, `dark`, `midnight_executive`, `forest_moss`, `terracotta`)
or pass a custom palette object. The engine handles all the
PowerPoint XML gotchas (text-frame padding, blank-layout selection,
slide size in EMUs, font fallbacks).

Prefer this over hand-rolling python-pptx scripts: it bakes in the
visual conventions from the upstream Anthropic `pptx` skill (varied
layouts, no plain title+bullet slides, bold titles, consistent
margins) and produces decks that look authored rather than templated.

## When to use
- The user asks for a deck / pitch / presentation / slides "from
  scratch" / from supplied data.
- A skill needs to materialise a structured output (KPIs, tables,
  bullets, narrative) as a `.pptx` deliverable.

## When NOT to use
- To **edit** an existing deck — use `pptx.merge` (cover + body),
  `pptx.split` (subset/reorder), or unpack the XML manually for
  surgical edits.
- For a PDF report — use `pdf.create`.
- For a spreadsheet — use `xlsx.write`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| output | string | yes | Destination `.pptx` path. Must end in `.pptx`. |
| slides | object[] | yes | Ordered list of slide objects (see below). |
| theme | string \| object | no | Theme name or custom palette. Default `"professional"`. |
| layout | string | no | `"16x9"` (default, 13.333×7.5in), `"16x10"`, `"4x3"`, `"wide"`. |
| title | string | no | Deck metadata: title. |
| author | string | no | Deck metadata: author. |
| subject | string | no | Deck metadata: subject. |
| page_numbers | bool | no | If true, draw `N / total` in the bottom-right of every slide (skipped on the cover). |
| overwrite | bool | no | If true, replace the output file if it already exists. |

## Slide types

Every slide is `{"type": "<name>", ...fields, "notes": "<optional>"}`.

| type | required fields | notable optional fields |
|---|---|---|
| `cover` | `title` | `subtitle`, `tagline` |
| `title` | `text` | `subtitle` |
| `section` | `title` | `label` (small caps eyebrow) |
| `content` | `title` | `subtitle`, `body`, `bullets` (`[str]` or `[{text, level}]`) |
| `two_column` | `title` | `left` and `right`: `{header?, items: [str\|{text}]}` |
| `kpi` | `title`, `items` | `items`: `[{label, value, delta?, color?}]` (2-6 cards) |
| `table` | `title`, `rows` | `header` (bool, default true) — first row styled as header |
| `chart` | `title`, `kind`, `labels`, `data` | `series_names`, `kind`: `bar`/`column`/`barh`/`line`/`pie`/`doughnut`/`area` |
| `image` | `title`, `path` | `caption` |
| `image_text` | `title`, `path` | `image_side` (`left`/`right`), `body`, `bullets` |
| `quote` | `text` | `attribution` |
| `conclusion` | `title` | `subtitle` |

All text fields take plain strings — colour, weight, and font are
controlled by the theme and the slide type, not by inline markup.

## Returns
```
{
  ok: true,
  data: {
    output: "<absolute path>",
    slide_count: <int>,
    size_bytes: <int>,
    theme: "<name>|custom",
    layout: "16x9|16x10|4x3|wide",
    slides_rendered: ["cover", "content", "kpi", ...]
  }
}
```

## Errors
- `invalid_input` — `output` does not end in `.pptx`, or `slides` is empty.
- `output_exists` — destination already exists and `overwrite=false`.
- `dependency_missing` — `python-pptx` is not installed.
- `create_failed` — the build raised (the message includes the cause).

## Examples

### Short pitch deck
Call:
```
pptx.create(
  output="/tmp/q4-pitch.pptx",
  theme="midnight_executive",
  title="Q4 Pitch",
  page_numbers=true,
  slides=[
    {"type": "cover", "title": "Q4 Strategy", "subtitle": "Project Lighthouse",
     "tagline": "Prepared for the executive team"},
    {"type": "section", "label": "Where we are", "title": "Q3 in review"},
    {"type": "kpi", "title": "Headline numbers", "items": [
      {"label": "ARR", "value": "$12.4M", "delta": "+24% YoY"},
      {"label": "Net new logos", "value": "37"},
      {"label": "Gross margin", "value": "72%"},
      {"label": "Burn", "value": "$1.1M/mo", "color": "#fee2e2"}
    ]},
    {"type": "content", "title": "What worked",
     "bullets": [
       "Channel partnerships drove 40% of new pipeline",
       "Self-serve trial → paid conversion at 14%",
       {"text": "EU launch shipped on schedule", "level": 0}
     ]},
    {"type": "two_column", "title": "Strengths vs. risks",
     "left":  {"header": "Strengths", "items": ["Brand recognition", "Engineering velocity"]},
     "right": {"header": "Risks",     "items": ["Concentration in 3 accounts", "Talent retention"]}},
    {"type": "chart", "kind": "bar",
     "title": "Quarterly revenue", "labels": ["Q1", "Q2", "Q3", "Q4"],
     "data": [[2.1, 2.6, 3.1, 4.6]], "series_names": ["Revenue ($M)"]},
    {"type": "table", "title": "Top accounts",
     "rows": [["Account", "ARR", "Owner"],
              ["Acme",    "$1.4M", "JR"],
              ["Globex",  "$1.1M", "PL"],
              ["Initech", "$0.9M", "AM"]]},
    {"type": "conclusion", "title": "Ship it.",
     "subtitle": "Next review: 2026-01-15"}
  ]
)
```

### Image + bullets
Call:
```
pptx.create(
  output="/tmp/product.pptx",
  theme="modern",
  slides=[
    {"type": "image_text", "title": "Roadmap",
     "path": "/tmp/screenshots/dash.png", "image_side": "left",
     "bullets": ["New analytics view", "SAML SSO", "Audit log export"]}
  ]
)
```

## See also
- `pptx.see` — render the resulting deck as page images for visual QA.
  **Always do this once after `pptx.create` and look for the issues
  listed in the PPTX skill QA checklist.**
- `pptx.convert` — export the deck to PDF.
- `pdf.create` — same idea for PDFs.

</details>

#### `pptx.extract_notes` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.extract_notes
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, notes]
---

# pptx.extract_notes

## Purpose
Return only the speaker notes for every (or selected) slide of a deck.
Equivalent to `pptx.extract_text(include_notes=true)` but without the
visible body text — useful when you want a clean view of the
presenter's narrative.

## When to use
- The user asks for "the speaker notes" / "the script" / "what the
  presenter says".
- You want to compare the on-slide content (already in `extract_text`)
  with the off-slide narrative (`extract_notes`).

## When NOT to use
- When the user wants the full slide content too — use
  `pptx.extract_text` with `include_notes=true`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |
| slides | string | no | 1-based slide spec; omit for every slide. |

## Returns
```
{
  ok: true,
  data: {
    slide_count: <int>,
    slides_with_notes: <int>,
    slides: [{ slide: <1-based>, notes: <str> }, ...]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `python-pptx` is not installed.
- `slide_out_of_range` / `invalid_input` — bad `slides` spec.

## Examples
### All notes
Call: `pptx.extract_notes(path="/tmp/deck.pptx")`

### Notes for slides 3-7
Call: `pptx.extract_notes(path="/tmp/deck.pptx", slides="3-7")`

## See also
- `pptx.extract_text` — full slide content plus optional notes.

</details>

#### `pptx.extract_text` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.extract_text
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, text]
---

# pptx.extract_text

## Purpose
Extract the visible text of every (or a selected subset of) slide in a
PowerPoint deck, plus the speaker notes by default. Walks every shape,
including tables and grouped shapes, joining lines per shape.

## When to use
- The user asks "what does the deck say" / "summarise these slides" /
  "what's on slide 5".
- A skill needs the text of specific slides to do downstream
  summarisation, translation, or comparison.
- You want notes too — they are returned alongside the slide body when
  `include_notes=true` (default).

## When NOT to use
- For visual layout, charts, embedded images, or anything appearance-
  related — use `pptx.see`.
- For speaker notes only — `pptx.extract_notes` returns the same data in
  a leaner shape.
- For converting the deck to PDF or rendering — use `pptx.convert` /
  `pptx.see`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |
| slides | string | no | 1-based slide spec like `"1"`, `"1-3"`, `"1,3-5,8"`. Omit for every slide. |
| include_notes | bool | no | If true (default), also return the speaker notes per slide. |

## Returns
On success:
```
{
  ok: true,
  data: {
    slide_count: <int>,
    char_count: <int>,
    slides: [
      { slide: <1-based>, title: <str|null>, text: <str>, notes: <str> },
      ...
    ]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input file.
- `dependency_missing` — `python-pptx` is not installed.
- `slide_out_of_range` / `invalid_input` — bad `slides` spec.

## Examples
### Whole deck
Call: `pptx.extract_text(path="/tmp/deck.pptx")`

### Slides 1-3 with notes
Call: `pptx.extract_text(path="/tmp/deck.pptx", slides="1-3", include_notes=true)`

### Slide 7 only, no notes
Call: `pptx.extract_text(path="/tmp/deck.pptx", slides="7", include_notes=false)`

## See also
- `pptx.read` — slide count + per-slide metadata first, before extracting.
- `pptx.extract_notes` — notes only.
- `pptx.see` — image renders for visual content.

</details>

#### `pptx.from_html` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.from_html
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, create, deck, html]
---

# pptx.from_html

## Purpose
Render a complete HTML document into a **picture-per-slide** PowerPoint
deck. Each rendered page becomes one slide; the design is the design
WeasyPrint produces — gradients, web fonts, full-bleed covers,
arbitrary aspect ratios, anything CSS can express. Same input
convention and same engine as `pdf.create`, so if you can render a PDF
you already know how to render a deck.

The trade: every slide is a single full-bleed Picture shape. **The
deck is presentation-grade, not edit-grade.** If the user will edit
the deck in PowerPoint after delivery, use `pptx.create` instead (its
element DSL produces native shapes, text boxes, tables, and charts).

## When to use
- The user wants a polished, design-rich deck for a meeting / review /
  client share — not something to edit downstream.
- You need design surface that `pptx.create` can't reach: custom
  fonts, gradients, exotic aspect ratios (square, portrait, social),
  arbitrary layouts.
- You already authored an HTML report with `html.create` (or by hand)
  and want a deck version of the same content.

## When NOT to use
- The user said "I'll tweak it in PowerPoint" → use `pptx.create`.
- The user wants a paginated document (PDF, report, memo) → use
  `pdf.create`.
- The deliverable is a web page → use `html.create`.

## Parameters
- `output` — destination `.pptx` path. Parent dirs are created.
- `html` — **either** a complete HTML document as a string (must start
  with `<!doctype html>` and contain `<html>` / `<head>` / `<body>`),
  **or** the absolute path to a `.html` / `.htm` file. Same rule as
  `pdf.create`: strings ≤ 1 KB, single-line, ending in `.html`/`.htm`
  are treated as a path; everything else is treated as raw HTML.

  **Critical:** declare exactly ONE `@page` rule. Its `size` becomes
  the slide size. Recommended:
  - 16:9 widescreen: `@page { size: 13.333in 7.5in; margin: 0 }`
  - 4:3 classic:     `@page { size: 10in 7.5in; margin: 0 }`
  - Square (social): `@page { size: 1080px 1080px; margin: 0 }`
  - Portrait story:  `@page { size: 1080px 1920px; margin: 0 }`

  Each slide is one HTML page, so use `break-before: page` on section
  containers to force a slide break, or size sections to exactly fill
  one page so they break naturally.

- `notes` — optional list of speaker-note strings, one per slide in
  slide order. Pass `null` for slides you don't want notes on. Length
  ≤ slide_count.
- `image_dpi` — rasterisation DPI, 36–600 (default 192). 192 looks
  crisp on Retina and 1080p projectors. Bump to 300+ for print, drop
  to 96 for cheap previews.
- `image_format` — `png` (default, lossless, transparency) or
  `jpeg` (smaller files on photo-heavy designs).
- `jpeg_quality` — 1–100 (default 88), used when `image_format='jpeg'`.
- `title`, `author`, `subject` — deck metadata (shows up in
  PowerPoint → File → Info and in search indexes).
- `engine` — `auto` (default) | `weasyprint` | `libreoffice`. Use
  WeasyPrint when at all possible: LibreOffice silently drops `@page`
  rules, which means your slide size won't be what you asked for.
- `timeout_seconds` — LibreOffice subprocess timeout (fallback path).
- `overwrite` — replace an existing output file.

## Returns
```jsonc
{
  ok: true,
  data: {
    output:          "<path>",
    size_bytes:      <int>,
    slide_count:     <int>,
    engine:          "weasyprint" | "libreoffice",
    image_format:    "png" | "jpeg",
    image_dpi:       <int>,
    slide_width_in:  <float>,   // derived from the @page size
    slide_height_in: <float>,
    warnings:        [<string>, ...]
  }
}
```

## Errors
- `invalid_input` — `output` isn't `.pptx`, `html` missing/empty/
  fragment, `image_dpi` out of range, `image_format` not png/jpeg,
  `notes` longer than the rendered deck, or the HTML file doesn't
  exist.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `pypdfium2` not installed, or WeasyPrint
  native libs unavailable AND `engine="weasyprint"` was forced.
- `render_failed` — intermediate PDF couldn't be opened / had zero
  pages / a specific page failed to rasterise.
- `create_failed` — catch-all for downstream python-pptx failures.

## Designing for slides (vs. pages)

The single biggest design difference between a slide and a PDF page:
**margin should usually be 0** and you should paint your own padding
inside the body. Otherwise WeasyPrint puts a hairline white border
around each slide and it looks like the deck was photocopied badly.

```html
<style>
  @page { size: 13.333in 7.5in; margin: 0 }
  body  { margin: 0; font: 18pt/1.45 'Inter', system-ui, sans-serif; color: #0f172a; }
  .slide {
    width: 13.333in; height: 7.5in;
    padding: 0.75in;
    box-sizing: border-box;
    page-break-after: always;   /* one .slide per slide */
    display: flex; flex-direction: column;
  }
  .slide:last-child { page-break-after: auto; }
  .slide.cover {
    padding: 0;
    background: radial-gradient(circle at 20% 0%, #312e81, #0f172a 70%);
    color: white;
    justify-content: flex-end;
  }
  .slide.cover .wrap { padding: 1in; }
  .slide.cover h1 { font-size: 84pt; font-weight: 800; letter-spacing: -0.02em; margin: 0; }
</style>
```

The `.slide { page-break-after: always }` trick is the standard way to
guarantee one HTML container = one slide. Size the container to your
`@page` exactly and you get pixel-precise control over each slide's
content.

## Examples

### Minimal — one-slide title card
```
pptx.from_html(
  output="/tmp/intro.pptx",
  html="""<!doctype html><html><head><meta charset='utf-8'>
    <style>
      @page { size: 13.333in 7.5in; margin: 0 }
      body  { margin: 0; font-family: 'Helvetica Neue', sans-serif; }
      .s    { width: 13.333in; height: 7.5in; background: #0f172a; color: white;
              display: flex; align-items: center; justify-content: center;
              text-align: center; flex-direction: column; }
      h1    { font-size: 80pt; margin: 0 0 0.5in; letter-spacing: -0.02em; }
      p     { font-size: 22pt; opacity: 0.7; margin: 0; }
    </style></head><body>
    <div class="s"><h1>Q4 Review</h1><p>CIB Gen-AI · January 8, 2026</p></div>
  </body></html>"""
)
```

### Multi-slide deck with speaker notes
```
pptx.from_html(
  output="/tmp/q4.pptx",
  title="Q4 Review",
  author="CIB Gen-AI",
  notes=[
    "Open with the bottom line — stock cover dropped 14%.",
    "Walk through the three drivers; don't read the numbers.",
    "Hand over to Sam for the remediation plan."
  ],
  html="""<!doctype html><html><head><meta charset='utf-8'>
    <link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap'>
    <style>
      @page { size: 13.333in 7.5in; margin: 0 }
      body  { margin: 0; font-family: 'Inter', sans-serif; color: #0f172a; }
      .slide { width: 13.333in; height: 7.5in; padding: 0.75in;
               box-sizing: border-box; page-break-after: always;
               display: flex; flex-direction: column; }
      .slide:last-child { page-break-after: auto; }
      .cover { padding: 0; background: radial-gradient(circle at 20% 0%, #312e81, #0f172a 70%);
               color: white; justify-content: flex-end; }
      .cover .wrap { padding: 1in; }
      .cover h1 { font-size: 84pt; font-weight: 800; letter-spacing: -0.02em; margin: 0; }
      .cover p  { font-size: 20pt; opacity: 0.7; }
      h2 { font-size: 40pt; font-weight: 800; margin: 0 0 0.4in; }
      .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3in; }
      .kpi  { background: #f1f5f9; border-radius: 0.15in; padding: 0.35in; }
      .kpi .v { font-size: 44pt; font-weight: 800; }
      .kpi .l { font-size: 14pt; color: #475569; text-transform: uppercase; letter-spacing: 0.04em; }
      .next  { text-align: center; flex: 1; display: flex;
               flex-direction: column; justify-content: center; }
      .next h1 { font-size: 64pt; font-weight: 800; margin: 0 0 0.3in; }
      .next p  { font-size: 22pt; color: #475569; margin: 0; }
    </style></head><body>
    <section class='slide cover'><div class='wrap'>
      <h1>Q4 Review</h1><p>CIB Gen-AI · January 8, 2026</p>
    </div></section>
    <section class='slide'>
      <h2>At a glance</h2>
      <div class='kpis'>
        <div class='kpi'><div class='l'>Stock cover</div><div class='v'>-14%</div></div>
        <div class='kpi'><div class='l'>SKUs</div><div class='v'>1,042</div></div>
        <div class='kpi'><div class='l'>Stockouts</div><div class='v'>37</div></div>
        <div class='kpi'><div class='l'>On-hand $</div><div class='v'>$4.2M</div></div>
      </div>
    </section>
    <section class='slide next'>
      <h1>Over to Sam</h1><p>Remediation plan</p>
    </section>
  </body></html>"""
)
```

### From an `html.create` report
```
pptx.from_html(
  output="/tmp/readout.pptx",
  html="/tmp/readout.html"
)
```
(Tip: when adapting an `html.create` report for slides, override
`@page` to your slide size and add `margin: 0` — the report's print
geometry was tuned for paper, not slides.)

## See also
- `pptx.create` — author an **editable** deck from a structured element
  DSL. Use this when the user will modify the deck downstream.
- `pdf.create` — same engine, paginated PDF output instead of a deck.
- `pptx.see` — visual QA on the produced deck (max 5 slides per call).
- `pptx.extract_notes`, `pptx.merge`, `pptx.split`, `pptx.convert` —
  operate on the produced deck further.

</details>

#### `pptx.merge` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.merge
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, combine]
---

# pptx.merge

## Purpose
Concatenate two or more `.pptx` files into a single deck. The output
inherits the slide master, theme, and slide size of the **first** input.
Slides from subsequent decks are appended in order; their shapes are
cloned onto a matching layout from the first deck (falling back to
"Blank" if no layout name matches).

## When to use
- The user wants to stitch together cover/body/appendix decks.
- A skill needs to bolt a programmatically-generated cover onto an
  existing deck.

## When NOT to use
- To rearrange slides inside a single deck — use `pptx.split` with a
  reordered `slides=` spec, then save as a new file.
- When you must preserve every decks' theme — `pptx.merge` standardises
  on the first input's theme. If themes diverge significantly, consider
  converting the others to images and rebuilding via `pptx.create`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| inputs | string[] | yes | List of `.pptx` paths, in the order to concatenate. At least 2. |
| output | string | yes | Destination `.pptx` path. |
| overwrite | bool | no | If true, replace the output file when it exists. |

## Returns
```
{
  ok: true,
  data: {
    output: "<path>",
    slide_count: <int>,
    source_count: <int>,
    appended: <int>   // slides added from inputs 2..N
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — fewer than 2 inputs, or output doesn't end in `.pptx`.
- `output_exists` — destination exists and `overwrite=false`.
- `merge_failed` — a slide copy failed (the message includes the source).
- `dependency_missing` — `python-pptx` is not installed.

## Examples
### Cover + body
Call:
```
pptx.merge(
  inputs=["/tmp/cover.pptx", "/tmp/body.pptx"],
  output="/tmp/full.pptx"
)
```

### Three-deck stitch with overwrite
Call:
```
pptx.merge(
  inputs=["/tmp/intro.pptx", "/tmp/main.pptx", "/tmp/appendix.pptx"],
  output="/tmp/full.pptx",
  overwrite=true
)
```

## See also
- `pptx.split` — extract a subset of slides into a new deck.
- `pptx.create` — author a fresh deck from structured data.

</details>

#### `pptx.read` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.read
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, metadata]
---

# pptx.read

## Purpose
Open a PowerPoint deck and return its metadata, slide dimensions, and a
per-slide overview (index, title, layout name, shape count, whether the
slide has speaker notes). Use this first whenever you need to know how
big a deck is or what's in it before calling a heavier extraction tool.

## When to use
- The user hands you a `.pptx` path and asks "what is this" / "how many
  slides" / "what's the deck about".
- A skill needs the slide count to drive a `slides=` argument in a
  follow-up call to `pptx.extract_text`, `pptx.split`, or `pptx.see`.
- You want to inventory slide layouts before reusing the deck as a
  template.

## When NOT to use
- For the actual text content — use `pptx.extract_text`.
- For visually inspecting a slide — use `pptx.see` (renders slides as
  images).
- For converting to PDF — use `pptx.convert`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved path>",
    slide_count: <int>,
    slide_width_emu: <int>,
    slide_height_emu: <int>,
    slide_width_in: <float>,
    slide_height_in: <float>,
    metadata: { title, author, subject, keywords, category, comments, last_modified_by },
    slides: [{ index, title, layout, shape_count, has_notes }, ...]
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file does not have a `.pptx` extension or is unreadable.
- `dependency_missing` — `python-pptx` is not installed in this environment.

## Examples
### Inspect a deck
Call: `pptx.read(path="/tmp/quarterly-update.pptx")`
Returns: `{ok: true, data: {slide_count: 18, metadata: {title: "Q4 Update"}, slides: [...]}}`

## See also
- `pptx.extract_text` — actual slide text content.
- `pptx.see` — rasterise slides as images for visual inspection.
- `pptx.convert` — turn the whole deck into a PDF.

</details>

#### `pptx.see` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.see
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, read, vision]
---

# pptx.see

## Purpose
Rasterise up to 5 slides of a PowerPoint deck and inject them into the
conversation as images, so the model can *look* at the slide rather than
only parse its text. Mirrors `pdf.see` for `.pptx` files: under the hood
the deck is converted to PDF once (`soffice --convert-to pdf`) and the
selected pages are rendered with `pypdfium2`.

## When to use
- The user asks about a chart, diagram, layout, icon, image, or visual
  treatment that text extraction cannot recover.
- `pptx.extract_text` returned nothing useful (the slide is image-heavy)
  and you need to see what's actually on it.
- You want to verify your own newly-authored deck (after `pptx.create`)
  looks right before declaring success. **Always render with `pptx.see`
  at least once after `pptx.create` and look for the issues listed in
  the QA checklist in the PPTX skill.**
- You want to compare two slides side by side.

## When NOT to use
- For the plain text body — `pptx.extract_text` is faster and feeds
  richer content per token.
- For tables that have an embedded text layer in the deck —
  `pptx.extract_text` already gives you cell text. `pptx.see` is for the
  visual content only.
- To process many slides at once — this tool refuses more than 5 slides
  per call (`too_many_slides`). Split the request or pick which 5
  matter most.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pptx` file. |
| slides | string | no | 1-based slide spec; max 5, e.g. `"1"`, `"2-4"`, `"1,3,5"`. Omit to render slide 1 only. |
| scale | float | no | Render scale; `2.0` ≈ 200 dpi. Keep ≤ `3.0` to stay within model image limits. Default `2.0`. |
| timeout_seconds | int | no | Hard limit on the LibreOffice subprocess (default 120). |

## Returns
On success:
```
{
  ok: true,
  data: {
    path: "<resolved>",
    slide_count: <total slides in deck>,
    rendered: [{ slide: <1-based>, bytes: <b64 length> }, ...],
    scale: <float>
  },
  images: [ToolImage, ...]   // attached to the next turn as multimodal content
}
```
The framework automatically appends the images to the next user turn so
the model can see them. The `data` payload itself is the textual
summary.

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `dependency_missing` — `pypdfium2` is not installed, or
  LibreOffice (`soffice`) is not on `PATH`.
- `slide_out_of_range` / `invalid_input` — bad `slides` spec.
- `too_many_slides` — more than 5 slides requested in a single call.
- `timeout` / `convert_failed` — LibreOffice failed to produce the
  intermediate PDF.
- `render_failed` — `pypdfium2` raised on a specific slide.

## Examples
### See slide 1
Call: `pptx.see(path="/tmp/deck.pptx")`

### See the appendix
Call: `pptx.see(path="/tmp/deck.pptx", slides="14-18")`

### See three scattered slides
Call: `pptx.see(path="/tmp/big-deck.pptx", slides="1,7,12")`

## See also
- `pptx.extract_text` — far cheaper for text content.
- `pptx.convert` — produce the PDF without rendering page images.
- `pptx.read` — to know the slide count before choosing which to render.

</details>

#### `pptx.split` &nbsp; <sub>v1 · internal · owner: team-doc-ai</sub>

<details><summary>card</summary>

---
tool: pptx.split
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, split]
---

# pptx.split

## Purpose
Extract a subset of slides from a deck (or reorder them) into a new
`.pptx` file. Preserves the deck's slide master, theme, and the order
given in `slides=`.

## When to use
- The user wants to keep slides 1-5 / 3,7,9 only.
- A skill needs to reorder slides (pass them in the new order).
- You need to share a single section of a long deck.

## When NOT to use
- To combine multiple decks — use `pptx.merge`.
- To author a brand-new deck — use `pptx.create`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to the source `.pptx` file. |
| slides | string | yes | 1-based slide spec to keep, e.g. `"1-5"` or `"1,3,7-9"`. Order is preserved. |
| output | string | yes | Destination `.pptx` path. |
| overwrite | bool | no | If true, replace the output file if it already exists. |

## Returns
```
{
  ok: true,
  data: {
    output: "<path>",
    slide_count: <int>,
    selected_slides: [<1-based slide numbers in output order>, ...]
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `invalid_input` — output doesn't end in `.pptx`, or `slides` spec is empty.
- `output_exists` — destination exists and `overwrite=false`.
- `slide_out_of_range` — `slides` spec refers to a missing slide.
- `split_failed` — XML manipulation failed (rare; message includes cause).
- `dependency_missing` — `python-pptx` is not installed.

## Examples
### Keep first five
Call: `pptx.split(path="/tmp/deck.pptx", slides="1-5", output="/tmp/intro.pptx")`

### Reorder
Call: `pptx.split(path="/tmp/deck.pptx", slides="3,1,2", output="/tmp/reordered.pptx")`

## See also
- `pptx.merge` — combine multiple decks.
- `pptx.read` — slide count before choosing a range.

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
- **combine** — `pdf.merge`, `pptx.merge`
- **convert** — `html.to_pdf`, `pptx.convert`, `xlsx.convert`
- **create** — `html.create`, `pdf.create`, `pptx.create`, `pptx.from_html`, `xlsx.write`
- **deck** — `pptx.create`, `pptx.from_html`
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
- **html** — `html.create`, `html.extract_text`, `html.read`, `html.see`, `html.to_pdf`, `pptx.from_html`
- **internal-docs** — `docstore.fetch`
- **meta** — `orchestrator.delegate`
- **metadata** — `html.read`, `pdf.read`, `pptx.read`, `xlsx.info`
- **metrics** — `text.word_count`
- **notes** — `pptx.extract_notes`
- **numeric** — `text.extract_lines`
- **ocr** — `pdf.ocr`
- **pack-authoring** — `repo.scaffold_pack`
- **pdf** — `pdf.create`, `pdf.decrypt`, `pdf.encrypt`, `pdf.extract_tables`, `pdf.extract_text`, `pdf.fill_form`, `pdf.form_fields`, `pdf.merge`, `pdf.ocr`, `pdf.read`, `pdf.rotate`, `pdf.see`, `pdf.split`
- **pptx** — `pptx.convert`, `pptx.create`, `pptx.extract_notes`, `pptx.extract_text`, `pptx.from_html`, `pptx.merge`, `pptx.read`, `pptx.see`, `pptx.split`
- **query** — `xlsx.sql`
- **read** — `docstore.fetch`, `html.extract_text`, `html.read`, `html.see`, `pdf.extract_tables`, `pdf.extract_text`, `pdf.form_fields`, `pdf.ocr`, `pdf.read`, `pdf.see`, `pptx.extract_notes`, `pptx.extract_text`, `pptx.read`, `pptx.see`, `repo.read_catalog`, `repo.read_doc`, `xlsx.info`, `xlsx.read`, `xlsx.sql`
- **recalc** — `xlsx.recalc`
- **reference** — `repo.read_catalog`, `repo.read_doc`
- **report** — `html.create`, `pdf.create`
- **routing** — `orchestrator.delegate`
- **scaffold** — `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`
- **search** — `repo.search_catalog`
- **security** — `pdf.decrypt`, `pdf.encrypt`
- **skill-authoring** — `repo.scaffold_skill`
- **smoke-test** — `core.echo`
- **split** — `pdf.split`, `pptx.split`
- **spreadsheet** — `xlsx.convert`, `xlsx.edit_cells`, `xlsx.format`, `xlsx.info`, `xlsx.read`, `xlsx.recalc`, `xlsx.sql`, `xlsx.write`
- **sql** — `xlsx.sql`
- **style** — `xlsx.format`
- **tabular** — `pdf.extract_tables`, `xlsx.read`
- **text** — `html.extract_text`, `pdf.extract_text`, `pptx.extract_text`, `text.extract_lines`, `text.word_count`
- **tool-authoring** — `repo.scaffold_tool`
- **transform** — `pdf.rotate`
- **vision** — `html.see`, `pdf.see`, `pptx.see`
- **write** — `html.create`, `html.to_pdf`, `pdf.create`, `pdf.decrypt`, `pdf.encrypt`, `pdf.fill_form`, `pdf.merge`, `pdf.rotate`, `pdf.split`, `pptx.convert`, `pptx.create`, `pptx.from_html`, `pptx.merge`, `pptx.split`, `repo.scaffold_pack`, `repo.scaffold_skill`, `repo.scaffold_tool`, `xlsx.convert`, `xlsx.edit_cells`, `xlsx.format`, `xlsx.recalc`, `xlsx.write`
