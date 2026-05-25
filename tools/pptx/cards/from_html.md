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
