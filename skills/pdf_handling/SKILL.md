---
name: pdf_handling
description: >
  Use this skill whenever the user gives you a `.pdf` path or asks to do
  anything with a PDF — read it, extract text or tables, look at a page,
  merge / split / rotate, encrypt or decrypt, fill a form, OCR a scan, or
  **author a brand-new PDF report / summary / one-pager from structured
  data** (use `pdf.create`). Append this skill on top of whatever pack is
  running; it composes cleanly with other skills. Do not use this skill
  for `.docx`, `.pptx`, or `.xlsx` files — there are (or will be)
  dedicated skills for those.
version: 0.1.0
---

# PDF handling

## When this skill applies

The user mentions a PDF file (path, attachment, or describes one) and wants
to read, transform, inspect, or fill it. Typical triggers:

- "What's in `<path>.pdf`?"
- "Extract the table on page 4 of `report.pdf`."
- "Merge these three PDFs."
- "Show me page 2 of the contract."
- "This is a scan — pull the text out."
- "Fill the W-9 with my details."
- "Strip the password from this PDF."
- "Make me a PDF presenting / summarising this data."
- "Generate a one-pager / report / memo as a PDF."

## Workflow

The right first move depends on what the user wants. Use this decision
table; each entry maps to a single tool call.

| User wants | First call |
|---|---|
| Quick overview ("what is this PDF?") | `pdf.read(path=...)` |
| The text body | `pdf.extract_text(path=..., pages=<optional>)` |
| Specific tables | `pdf.extract_tables(path=..., pages=<optional>)` |
| To *see* a page (charts, layout, signatures) | `pdf.see(path=..., pages="1")` (max 5 pages) |
| OCR a scanned PDF | First `pdf.extract_text` to confirm no text layer; then `pdf.ocr(path=..., lang=...)` |
| Merge | `pdf.merge(inputs=[...], output=...)` |
| Split / extract pages | `pdf.split(path=..., pages=..., output=...)` |
| Rotate | `pdf.rotate(path=..., degrees=..., pages=<optional>, output=...)` |
| Add password | `pdf.encrypt(path=..., user_password=..., output=...)` |
| Remove password | `pdf.decrypt(path=..., password=..., output=...)` |
| Inspect a form's fields | `pdf.form_fields(path=...)` |
| Fill a form | `pdf.form_fields` first, then `pdf.fill_form(values={...}, output=...)` |
| **Author a brand-new PDF** (report, summary, one-pager) | `pdf.create(output=..., html="<!doctype html>…")` — write a complete HTML document (or pass a `.html` file path). |

### The standard sequence for "tell me about this PDF"

1. `pdf.read(path=<path>)` to get `page_count`, `encrypted`, metadata.
2. If `encrypted=true`, ask the user for the password. Do not guess.
3. Try `pdf.extract_text(path=<path>, pages="1-<min(page_count,3)>")` for a
   sample.
4. If the sample text is empty or whitespace-only, the document is almost
   certainly a scan. Call `pdf.see(path=..., pages="1")` to confirm
   visually, then fall back to `pdf.ocr` if the user wants the text.
5. Summarise what you found: page count, document title (if any), whether
   it's a scan, and a one-paragraph gist from the sample text.

### Visual inspection — `pdf.see`

- Use `pdf.see` whenever the user's question is about *appearance*: a chart,
  a stamp, a signature, the layout, "does this look right?".
- Cap each call at 5 pages. If the user wants 10, ask whether the first 5
  are the priority or split the task.
- Render at the default `scale=2.0` unless the user reports unreadable
  images, in which case bump to `3.0`.
- After the call, the images are attached to your next turn automatically.
  Reference them ("looking at page 1 of the rendered images, the chart …")
  rather than re-emitting them.

### Authoring a new PDF — `pdf.create`

This is the right tool whenever the user wants a PDF *produced* (a
report, summary, presentation, one-pager, memo, KPI dashboard, etc.).
**Do not refuse the request and do not fall back to writing a `.xlsx`
"the user can export from Excel"** — `pdf.create` exists exactly so you
can deliver the PDF directly.

**What `pdf.create` is.** A renderer. You supply a complete HTML
document, it renders it to PDF using WeasyPrint (LibreOffice fallback).
The tool does **not** wrap fragments, inject styling, or override your
`@page` rule — the document you write is the document that gets
printed. That gives you the full design surface of a modern browser
*plus* the CSS Paged Media extensions: named pages, running headers and
footers, page counters, repeated table headers, custom page sizes,
embedded web fonts, full-bleed covers.

The tool takes one input either way:

- **A complete HTML string** — must start with `<!doctype html>` and
  include `<html>` / `<head>` / `<body>`. Put your `@page` rule and
  styling in a `<style>` block in the head. The full design crash
  course is in `tools/pdf/cards/create.md`.
- **A path to a `.html` / `.htm` file** — e.g. one produced by
  `html.create`. Strings ≤ 1 KB that look like a file path are treated
  as such; everything else is treated as raw HTML.

Workflow:

1. **Gather the data first.** If the source is a spreadsheet, use
   `xlsx.sql` to pre-aggregate the numbers you want to show (totals,
   top-N, breakdowns); don't dump raw rows into the PDF. If the source
   is another PDF or text, use `pdf.extract_text` / `extract_tables`.
2. **Decide the design.** Pick page size (`A4` for EU, `letter` for
   US; landscape / custom for one-pagers and posters), margin, font,
   and palette. For a multi-page document plan a running header and
   page counter in the `@page` rule.
3. **Compose the HTML.** Two good patterns:
   - **From scratch.** Start with `<!doctype html><html><head><style>
     @page { … }</style></head><body>…</body></html>` and build the
     content directly. Use CSS Grid / Flex for KPI rows, `<table>` for
     tabular data, inline SVG for vector charts.
   - **From `html.create`.** Call `html.create(elements=[…],
     path="/tmp/draft.html")` to get a themed, well-structured report
     on disk, then read it, splice in your own `@page` rule / fonts /
     palette tweaks, save under a new path, and pass that path to
     `pdf.create`. Fastest way to get a polished result.
4. **Call `pdf.create`** with `output=<same-dir-as-source>/<name>.pdf`
   and your HTML (or path). Set `title=` / `author=` / `subject=` for
   searchable PDF metadata. Use `overwrite=true` only if the user
   explicitly asked to replace the file.
5. **Verify.** If the user might want to check the look, follow up
   with `pdf.see(path=<output>, pages="1")` so they see the cover
   rendered.

Notes:
- **CSS Paged Media is your friend.** `@page { @top-left { content:
  "…" } @bottom-right { content: counter(page) " / " counter(pages) }
  }` gives you running headers and page counters with no JavaScript
  and no template engine. `break-inside: avoid` keeps cards intact.
  `thead { display: table-header-group }` repeats table headers on
  every page. `page: cover; break-before: page` swaps page geometry
  per section.
- **Web fonts work.** `<link rel="stylesheet"
  href="https://fonts.googleapis.com/...">` or `@font-face` with a
  `woff2` URL. Subset-embedded in the PDF.
- **Format numbers yourself** (`"$1,234.56"`, `"12.4%"`) — the tool
  doesn't auto-format anything.
- For very large tables (> ~30 rows), summarise the long tail in a
  trailing row ("… plus 412 more") rather than paginating manually.
- If the user asks for an Excel-to-PDF "export", do NOT round-trip
  through Excel. Read the workbook, build the HTML, render with
  `pdf.create`.
- **`dependency_missing` from `pdf.create`** usually means WeasyPrint's
  native libs (Pango/Cairo) are absent. The error message includes
  the exact install line. The auto fallback to LibreOffice handles
  this transparently in most environments — but `@page` margin boxes
  (running headers, page counters) are silently dropped on that path,
  and a warning is attached to the result.

### Forms

1. Always call `pdf.form_fields(path=...)` first. If `fillable=false`, tell
   the user the PDF is not a fillable form — do not attempt `pdf.fill_form`.
2. Show the user the field names you found and ask for the values.
3. Call `pdf.fill_form(path=..., values={...}, output=...)`.
4. Offer to `pdf.see` the output so the user can verify.

### Encrypted PDFs

- `pdf.read`, `pdf.extract_text`, and other read-side tools will fail with
  `password_required` on an encrypted PDF. Surface that error to the user
  and ask for the password; do not retry blindly.
- If the user provides one, use `pdf.read(path=..., password=...)` to
  confirm, then either pass `password=...` to subsequent reads (where
  supported) or call `pdf.decrypt` once and operate on the unencrypted copy.

## Conventions

- **Page numbers are 1-based** in every tool's `pages` argument. The model
  output should also speak in 1-based numbers. Never write "index 0".
- **Page spec syntax** is `"1"`, `"1-5"`, `"1,3,7-9"`. No spaces.
- **Never overwrite the user's input file.** Always write to a new `output`
  path. If the user explicitly asks to replace, pass `overwrite=true` but
  warn them once in the reply.
- **Output paths**: prefer the same directory as the input, with a suffix
  like `-merged.pdf`, `-rotated.pdf`, `-pages-1-5.pdf`. If the user did not
  specify, propose one and proceed.
- **OCR is a last resort.** It is slow, lossy, and language-sensitive. Try
  `pdf.extract_text` first; if it returns empty/whitespace, confirm with
  `pdf.see`, then call `pdf.ocr` with the right `lang=`.
- **Big PDFs**: if `page_count > 50` and the user did not narrow, summarise
  the document with the first few pages and ask which range they care about
  before extracting everything.

## Edge cases

- **`file_not_found`**: ask the user for a corrected path; do not list
  files or guess.
- **`unsupported_format`**: the file is not a PDF or is corrupt. Suggest
  the user verify the file; if the extension is `.docx`/`.pptx`/`.xlsx`,
  point them at the right skill.
- **`dependency_missing`** on `pdf.extract_tables`, `pdf.ocr`, or `pdf.see`:
  tell the user the runtime is missing `pdfplumber` / `pytesseract` /
  `pypdfium2`. Do not retry.
- **`page_out_of_range`**: re-read with `pdf.read` to get the true page
  count, then re-issue with a valid range.
- **`too_many_pages`** from `pdf.see`: split the request into ≤5-page calls
  or ask which 5 pages matter most.
- **`no_form_fields`** from `pdf.fill_form`: the PDF is a flat form, not a
  fillable one. Tell the user and stop; do not attempt to overlay text.
- **`password_required`**: do not retry with guessed passwords. Ask once.

## References

- The Anthropic upstream `pdf` skill (in `anthropic-skills/skills/pdf/`)
  documents the underlying Python libraries (pypdf, pdfplumber,
  pypdfium2). This skill exposes the same capabilities as tool calls
  (including PDF authoring via `pdf.create`); do not shell out or write
  Python yourself.
- `pdf.create` is a thin HTML→PDF renderer on top of WeasyPrint
  (LibreOffice fallback). See `tools/pdf/cards/create.md` for the full
  design crash course and `tools/pdf/create.py` for the implementation.
