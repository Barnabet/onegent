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
