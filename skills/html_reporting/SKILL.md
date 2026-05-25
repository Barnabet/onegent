---
name: html_reporting
description: >
  Use this skill whenever a sub-agent needs to produce a **report** as a
  deliverable and the user did NOT request a specific other file format
  (`.pdf`, `.pptx`, `.docx`, `.xlsx`). HTML is the default reporting
  format on this platform — single-file, self-contained, print-ready,
  WCAG-aware, and richer than Markdown for anything past ~100 lines.
  This skill also covers reading and rendering existing `.html` /
  `.htm` files (extract text, page screenshots, PDF export). The
  supervisor (router) should append this skill via `extra_skills` to
  any sub-agent it estimates will produce a report. Do not use this
  skill for short chat replies, code snippets, or single tables — those
  should stay as plain text or use the spreadsheet skill.
version: 0.1.0
---

# HTML reporting

## Background — why HTML is the default

In May 2026 Anthropic's engineering team (Thariq Shihipar, Claude Code
lead) published *"The Unreasonable Effectiveness of HTML"*, arguing
that HTML has overtaken Markdown as the right output format for agent
deliverables. The short version:

1. **Information density.** HTML packs tables, SVG charts, callouts,
   collapsibles, multi-column layouts, and images into one file. Markdown
   tops out at paragraphs, lists, and simple tables.
2. **Survives length.** Past ~100 lines, a Markdown file is unreadable.
   HTML structures (TOC, headings, sections, collapsibles) make a
   long document actually navigable.
3. **Sharing.** A self-contained `.html` opens in any browser with one
   click. No toolchain, no conversion, no install.
4. **Print-readiness.** A `@media print` block makes the same HTML
   produce a clean PDF when the recipient hits Print.
5. **Joy / engagement.** Stakeholders actually read HTML reports
   because they look authored.

This platform's `html.create` tool bakes the entire pattern in (inline
CSS, inline SVG, base64 images, system fonts, print-ready CSS, WCAG
contrast). **You should never hand-roll HTML or write a Python
template — call `html.create` instead.**

## When this skill applies

The sub-agent's task involves producing a **report** of any kind:

- Weekly / monthly status update
- Audit / compliance write-up
- Research summary / market analysis
- Decision document / RFC
- Incident post-mortem
- Project plan with timeline and risks
- Analytical write-up of spreadsheet data
- "Tell me about this dataset / file" beyond a few sentences
- Anything else the supervisor flagged as deserving a written report

Also: anytime the user hands you a `.html` / `.htm` file and asks
about it (use `html.read` / `html.extract_text` / `html.see`).

**The supervisor's rule of thumb:** if the user asked for "real work"
on something that will benefit from a structured deliverable, and they
did NOT specify the output format, add `html_reporting` to the
sub-agent's `extra_skills`. If they did specify (`.pdf` / `.pptx` /
`.xlsx`), use that format's skill instead.

## When NOT to use this skill

- Output is a one-paragraph chat answer → just reply in plain text.
- Output is a single small table that fits in chat → reply in plain
  text or Markdown.
- Output is a spreadsheet workbook the user wants to edit → use
  `xlsx_handling`.
- Output is a pitch deck or presentation → use `pptx_handling`.
- User explicitly asked for `.pdf` → use `pdf_handling`.
- Output is meant to be edited collaboratively in Git → keep it as
  Markdown.

## Tools

| Tool | Purpose |
|---|---|
| `html.create` | Author a brand-new self-contained HTML report (the default deliverable). |
| `html.read` | Get title, size, element counts, self-contained flag of an existing HTML file. |
| `html.extract_text` | Pull the readable text out of an HTML file. |
| `html.see` | Rasterise up to 5 pages of an HTML file and inject as images (mirrors `pdf.see`). |
| `html.to_pdf` | Convert HTML to PDF via LibreOffice (honours the `@media print` block). |

## Authoring workflow

### 1. Plan the document **before** calling `html.create`

A great report has clear structure. Decide upfront:

- **What's the headline?** It belongs in a `cover` (one paragraph or
  one line) at the top.
- **What are the 2-6 numbers that matter?** They go in a `kpi_row`
  immediately after the cover.
- **What sections are there?** Each gets a `heading` (level 2),
  ideally with an `id` so the `toc` element can link to it.
- **What chart(s) tell the story?** Use a `chart` (bar / line / pie).
  Charts are inline SVG; no external deps.
- **What does the reader need to take away?** End with a
  `callout` (variant `success`/`warning`/`danger`) or a `banner`.

### 2. Gather data first

If the report is about a spreadsheet, run `xlsx.sql` first to pre-
aggregate the numbers. If it's about a PDF, run `pdf.extract_text` /
`pdf.extract_tables`. Don't pour raw rows into the report — the
reader wants the headline.

### 3. Pick a theme

- `professional` (default) — most business reports.
- `modern` — product / marketing / launch announcements.
- `minimal` — technical reviews, audits, compliance.
- `vibrant` — internal celebrations, brand-heavy reports.
- `dark` — dashboards, ops post-mortems where colour matters.
- Custom palette — when the user supplies brand colours.

### 4. Call `html.create`

- Always set a `title` — it becomes the browser tab and the
  document metadata.
- Add an on-screen `header` / `footer` for context (project name,
  date, classification). They are hidden when the document is
  printed, so the printed PDF stays clean.
- For multi-section reports (≥ 3 H2s), add a `toc` element with
  anchors that match `heading` `id`s.
- For numbers, format them yourself (`"$1,234.56"`, `"12.4%"`); the
  tool does not auto-format.
- Inline markup allowed in text fields: `<b>`, `<i>`, `<u>`,
  `<code>`, `<br>`, `<a href="...">`. Anything else is escaped.

### 5. **Always verify with `html.see`**

This is not optional. After `html.create`, render the first 1-2
pages with `html.see` and look for the issues listed in the QA
checklist below. If you find problems, fix them and re-render. **Do
not declare the report done on the first render alone.**

### 6. (Optional) Export to PDF

If the user wants a PDF too (or always — useful for sharing via
email), follow up with `html.to_pdf(path=…, output=…)`. The HTML
already ships with a `@media print` block, so the PDF is clean.

## Layout cheat sheet

| What you want | Element |
|---|---|
| Headline cover | `cover` |
| Section header | `heading` (level 2) |
| Big numbers | `kpi_row` |
| Comparison / trend | `chart` |
| Tabular data | `table` |
| Side-by-side | `columns` |
| Status / take-away | `callout` (info/tip/note/success/warning/danger) |
| Quote | `quote` |
| Project schedule | `timeline` |
| Long, optional detail | `details` (collapsible) |
| Linkable contents | `toc` + `heading` with `id` |
| Image | `image` (always with `alt`) |

## QA checklist (run after every `html.create`)

**Assume there are problems on first render. Your job is to find them.**

Call `html.see` on at least page 1 (and the page containing your
main chart / table) and look for:

- Text overflow or cut-off in cards / callouts (often when the user-
  supplied value is much longer than the layout expected).
- Chart bars that touch axis text or labels that overlap. If so,
  shorten labels or split into two charts.
- Tables with more than ~10 rows on one page — consider grouping or
  using `details` to collapse the long tail.
- Low-contrast text when using a custom theme — the engine ships
  themes with ≥ 4.5:1 contrast, but a custom palette can break that.
- Empty / placeholder areas (e.g. you passed `bullets` but the
  element type was `table` — wrong shape silently rendered empty).
- Repeated monotone layout (five `paragraph` elements in a row) —
  break it up with a `callout`, `kpi_row`, `chart`, or `card`.

If you fix the spec and re-render, also re-call `html.see` on the
fixed page to confirm.

## Naming + output conventions

- **Output path**: prefer the same directory as the input data file
  if there is one. Use a stable, descriptive name like
  `q4-status.html`, `audit-2026-05.html`, `lighthouse-weekly.html`.
- **Title** in `html.create` should be the human-readable name of the
  report (e.g. "Project Lighthouse — Weekly Status, Week 21 2026"),
  not just "Report".
- **Never overwrite** the user's input file. Pick a new `output`
  path. If they explicitly asked to replace, pass `overwrite=true`
  and warn them once in the reply.

## Reading existing HTML

For an attached `.html` file:

1. `html.read(path=…)` first — title, size, counts, self-contained flag.
2. `html.extract_text(path=…)` if the user wants to summarise / quote.
3. `html.see(path=…, pages="1")` if the user asks about layout, a
   chart, or the visual treatment.

## Edge cases + errors

- **`dependency_missing`** on `html.see` / `html.to_pdf`: either
  `pypdfium2` is not installed or LibreOffice (`soffice`) is not on
  `PATH`. Tell the user and stop. Suggest opening the HTML in a
  browser directly.
- **`output_exists`**: ask the user; do not overwrite silently.
- **`create_failed`**: the message includes the element index and
  type. Fix that element and retry — most often it's a missing
  required field (e.g. `image` without `alt`, `chart` without
  `labels` / `data`).
- **`too_many_pages`** on `html.see`: split into multiple calls of
  ≤ 5 pages each.
- **Long report (`size_bytes` > ~2 MB)**: usually means a large
  base64-embedded image. That's fine for portability but slow to
  open. Suggest a smaller image if the user is going to share by
  email.

## References

- Thariq Shihipar (Anthropic), *Using Claude Code: The Unreasonable
  Effectiveness of HTML*, Nov 2026 — the source of the "single-file
  rule" and the print-readiness pattern.
- Lenny Rachitsky's *How I AI* podcast, *HTML is the new Markdown*,
  May 2026 — the broader case for HTML-as-default.
- The Anthropic upstream `pdf` skill (in `anthropic-skills/skills/pdf/`)
  for the visual-QA mindset that this skill borrows ("assume there
  are problems on first render").
