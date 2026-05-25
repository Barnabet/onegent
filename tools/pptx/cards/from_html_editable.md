---
tool: pptx.from_html_editable
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pptx, write, create, deck, html, editable]
---

# pptx.from_html_editable

## Purpose
Render a complete HTML document into a **fully editable** PowerPoint
deck. Each slide is a real PPTX slide with native text boxes, rounded
rectangles, tables, and pictures — not a flattened image. Users can
double-click the title, change a colour, edit a table cell, swap a
photo, the lot.

The pipeline is:

1. Load the HTML in a headless Chromium via Playwright.
2. For each `<section class="slide">`, walk every visible element and
   read its **computed style** + **bounding rect** straight from the
   browser. This way flex/grid/web-fonts/gradients all resolve to the
   exact same pixels the design produces.
3. Replay each element as a native python-pptx shape on a fresh
   slide. Backgrounds and borders become rounded rectangles;
   text-leaf elements become text boxes with one styled run per text
   node; tables become real PPTX tables; `<img>` become pictures;
   `<svg>` become embedded PNGs (vector-EMF support is a planned
   upgrade).

## When to use vs. `pptx.from_html`

| You need... | Use |
|---|---|
| The user can edit the deck after delivery | **`pptx.from_html_editable`** ← this tool |
| Pixel-perfect fidelity, exotic CSS effects (`filter`, `clip-path`, complex masks), output will only be presented | `pptx.from_html` |
| The user will tweak the deck *and* you want every shape native | this tool |

## When NOT to use
- The deliverable is a PDF → use `pdf.create`.
- The deliverable is a webpage → use `html.create`.
- You're authoring from a structured spec and don't already have HTML
  → use `pptx.create` (its DSL is the most direct path to native
  PPTX shapes; you save the browser hop entirely).

## Parameters
- `output` — destination `.pptx` path. Parent dirs are created.
- `html` — either a complete HTML document string (must start with
  `<!doctype html>`), or the absolute path to a `.html`/`.htm` file.
  **Each `<section class="slide">` (or any element with `class="slide"`)
  becomes one slide.** Size each slide container exactly:

  ```css
  .slide { width: 13.333in; height: 7.5in; box-sizing: border-box; }
  ```

  16:9 widescreen is `13.333in × 7.5in`. 4:3 is `10in × 7.5in`.
  Anything CSS can express works.

- `notes` — optional list of speaker-note strings, one per slide.
  Pass `null` for slides you want to skip.
- `title`, `author`, `subject` — deck metadata.
- `timeout_seconds` — Playwright timeout (default 60).
- `overwrite` — replace an existing output file.

## Returns
```jsonc
{
  ok: true,
  data: {
    output:          "<path>",
    size_bytes:      <int>,
    slide_count:     <int>,
    engine:          "playwright",
    editable:        true,
    slide_width_in:  <float>,
    slide_height_in: <float>,
    warnings:        [<string>, ...]
  }
}
```

## Errors
- `invalid_input` — `output` isn't `.pptx`, `html` missing or empty,
  no `.slide` containers in the document, or `notes` longer than the
  slide count.
- `output_exists` — destination exists and `overwrite=false`.
- `dependency_missing` — `python-pptx` not installed, Playwright not
  installed, or `playwright install chromium` was never run on this
  machine.
- `render_failed` — Playwright couldn't load the page or evaluate
  the extractor.
- `create_failed` — catch-all for downstream python-pptx failures.

## Supported CSS features
- **Layout:** flex, grid, absolute/relative positioning, padding,
  margin, `box-sizing` — anything Chromium can compute.
- **Backgrounds:** solid colours (with alpha), `linear-gradient`
  with explicit colour stops.
- **Borders:** uniform border colour + width, `border-radius`.
- **Text:** font family, size, weight, italic, colour, alignment,
  `<br>`, mixed inline runs (`<b>`/`<i>`/`<font>`), underline.
- **Images:** `<img>` with data URIs, http(s), file://, bare paths.
- **Tables:** `<table>` with per-cell text + background.
- **Transforms:** rotate (from `transform: rotate(Xdeg)`).
- **Opacity:** on solid-fill shapes and gradient stops.

## Known limitations
- `box-shadow`, `filter`, `clip-path`, `backdrop-filter` are ignored.
- `radial-gradient` and `conic-gradient` are ignored (fall back to
  the element's solid `background-color` if any).
- Per-corner `border-radius` falls back to the top-left corner.
- Per-side border styles are not yet supported (uses the top border).
- `<svg>` content is embedded as a raster screenshot, not a vector
  shape (vector embedding is on the roadmap).
- Web fonts render in the browser correctly, but the PPTX records
  only the font *name*; viewers without that font installed will see
  a fallback. Use system fonts when fidelity in PowerPoint matters.

## Examples

```
pptx.from_html_editable(
  output="/tmp/q4.pptx",
  title="Q4 Review",
  html="""<!doctype html><html><head><meta charset='utf-8'>
    <style>
      body { margin: 0; font-family: 'Helvetica Neue', sans-serif;
             color: #0f172a; }
      .slide { width: 13.333in; height: 7.5in; padding: 0.75in;
               box-sizing: border-box; position: relative; }
      .cover { background: linear-gradient(135deg, #312e81, #0f172a);
               color: white; }
      .cover h1 { font-size: 64pt; font-weight: 800; margin: 2in 0 0.3in; }
      .cover p  { font-size: 20pt; opacity: 0.7; }
      h2 { font-size: 32pt; margin: 0 0 0.3in; }
      .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3in; }
      .kpi  { background: #f1f5f9; border-radius: 0.15in; padding: 0.35in; }
      .kpi .v { font-size: 36pt; font-weight: 800; }
      .kpi .l { font-size: 12pt; color: #475569; text-transform: uppercase; }
    </style></head><body>
    <section class='slide cover'>
      <h1>Q4 Review</h1><p>CIB Gen-AI · January 8, 2026</p>
    </section>
    <section class='slide'>
      <h2>At a glance</h2>
      <div class='kpis'>
        <div class='kpi'><div class='l'>Stock cover</div><div class='v'>-14%</div></div>
        <div class='kpi'><div class='l'>SKUs</div><div class='v'>1,042</div></div>
        <div class='kpi'><div class='l'>Stockouts</div><div class='v'>37</div></div>
        <div class='kpi'><div class='l'>On-hand</div><div class='v'>$4.2M</div></div>
      </div>
    </section>
  </body></html>"""
)
```

Open the resulting `.pptx`: the title is a real text box, every KPI
card is a rounded rectangle, every value is its own editable run.

## See also
- `pptx.from_html` — same input, but flattens each slide to a
  picture. Pixel-perfect, not editable.
- `pptx.create` — author native shapes from a structured spec
  without the HTML hop.
- `pptx.see` — visual QA on the produced deck.
