---
name: pptx_handling
description: >
  Use this skill whenever the user gives you a `.pptx` path or asks to do
  anything with a PowerPoint deck — read it, extract text or speaker
  notes, look at a slide, merge / split decks, convert to PDF, or
  **author a brand-new presentation / pitch / deck from structured
  data** (use `pptx.create`). Trigger on any mention of "slides",
  "deck", "presentation", or a `.pptx` filename, regardless of what the
  user plans to do with the content afterwards. Append this skill on
  top of whatever pack is running; it composes cleanly with other
  skills. Do not use this skill for `.pdf`, `.docx`, or `.xlsx` files —
  there are dedicated skills for those.
version: 0.1.0
---

# PPTX handling

## When this skill applies

The user mentions a PowerPoint file (path, attachment, or describes one)
and wants to read, transform, inspect, or create it. Typical triggers:

- "What's in `<path>.pptx`?"
- "Summarise this deck."
- "Show me slide 4."
- "What do the speaker notes say?"
- "Merge these three decks."
- "Pull out slides 5-10 as a separate file."
- "Convert this deck to PDF."
- "Make me a pitch deck / presentation / slides about <topic>."

## Workflow

The right first move depends on what the user wants. Use this decision
table; each entry maps to a single tool call.

| User wants | First call |
|---|---|
| Quick overview ("what is this deck?") | `pptx.read(path=...)` |
| The slide text | `pptx.extract_text(path=..., slides=<optional>)` |
| Just the speaker notes | `pptx.extract_notes(path=..., slides=<optional>)` |
| To *see* a slide (charts, layout, images) | `pptx.see(path=..., slides="1")` (max 5 per call) |
| Merge decks | `pptx.merge(inputs=[...], output=...)` |
| Extract / reorder slides | `pptx.split(path=..., slides=..., output=...)` |
| Export to PDF | `pptx.convert(path=..., output=...pdf)` |
| **Author a brand-new deck** (pitch, summary, presentation) | Three options — pick before composing: `pptx.create(output=..., slides=[...])` for a structured-DSL **editable** deck; `pptx.from_html_editable(output=..., html="<!doctype html>…")` for an **editable** deck built from arbitrary HTML/CSS (best of both worlds); `pptx.from_html(output=..., html="<!doctype html>…")` for a **pixel-perfect picture-per-slide** deck rendered from HTML. |

### The standard sequence for "tell me about this deck"

1. `pptx.read(path=<path>)` to get `slide_count`, slide titles, layouts.
2. `pptx.extract_text(path=<path>, slides="1-<min(slide_count,3)>")` for a
   sample of the body text (notes included by default).
3. If the sample text is empty / whitespace-only on slides that the
   `read` call reported as having many shapes, the deck is probably
   image-heavy. Call `pptx.see(path=..., slides="1")` to confirm
   visually.
4. Summarise what you found: slide count, deck title (if any), a
   one-paragraph gist from the sample, and call out anything
   image-heavy that the model couldn't read as text.

### Visual inspection — `pptx.see`

- Use `pptx.see` whenever the user's question is about *appearance*: a
  chart, a diagram, a layout, an image, "does this look right?".
- Cap each call at 5 slides. If the user wants 10, ask whether the
  first 5 are the priority or split the task.
- Render at the default `scale=2.0` unless the user reports unreadable
  images, in which case bump to `3.0`.
- The first call to `pptx.see` for a given deck is slow (LibreOffice
  has to convert the whole deck to PDF). Subsequent calls in the same
  process are still slow — there is no cache. Prefer batching the
  slides you want into one call.
- After the call, the images are attached to your next turn
  automatically. Reference them ("looking at slide 3 of the rendered
  images, the chart …") rather than re-emitting them.

### Authoring a new deck — three tools, one decision

Three tools, distinct trade-offs. **Pick before you start composing,
and pick the right one for *what the user actually asked for*.**

- **`pptx.create`** — structured element DSL (`cover`, `kpi`, `chart`,
  `two_column`, …). Output is a **native, editable** deck: every shape,
  text frame, table, and chart can be clicked in PowerPoint and
  modified. Use when the user will tweak the deck, when they need real
  PowerPoint charts (not images of charts), or when they need a
  theme-driven look that downstream colleagues can re-theme. **Default
  choice for routine business decks** where the layouts in the DSL are
  enough.
- **`pptx.from_html_editable`** — you write a complete HTML document;
  each `<section class="slide">` becomes one slide. Output is a
  **native, editable** deck (text boxes, rounded rectangles, real
  tables, pictures) — same edit-ability as `pptx.create`, but the
  design surface is the full browser: CSS Grid/Flex, gradients,
  `border-radius`, custom KPI cards, anything you can express in HTML.
  **Default choice when the user wants editability *and* design
  freedom, or when they explicitly say "use the HTML editable way" /
  "from HTML" / "editable HTML deck".** Don't fall back to
  `pptx.create` if the user asked for the HTML route — that's
  ignoring the instruction.
- **`pptx.from_html`** — HTML in, full-bleed **Picture** per slide
  out. **Not editable** (each slide is a single image) but
  pixel-perfect: web fonts, `filter`, `clip-path`, exotic aspect
  ratios (square, portrait, social), anything CSS can express renders
  exactly as designed. Use for presentation-only decks where look
  beats edit-ability — a one-shot client read-out, a polished launch
  deck, a social-format carousel.

#### Quick picker
- User said *"editable"*, *"so I can modify it"*, *"I'll tweak it"* →
  `pptx.create` or `pptx.from_html_editable` (never `pptx.from_html`).
- User said *"from HTML"*, *"editable HTML"*, *"the HTML way"*,
  *"editable from HTML"* → **`pptx.from_html_editable`**. Do not
  substitute `pptx.create`.
- User wants a stock business deck and didn't mention HTML →
  `pptx.create`.
- User wants something visually distinctive and won't edit afterwards
  → `pptx.from_html`.

Whichever tool fits, **deliver the PowerPoint directly** — do not
refuse the request or fall back to a `.pdf` / `.docx` "the user can
adapt".

#### `pptx.create` — when the user will edit the deck

1. **Gather the data first.** If the source is a spreadsheet, use
   `xlsx.sql` to pre-aggregate the numbers you want to show. If the
   source is a PDF or text, use `pdf.extract_text` /
   `pdf.extract_tables`. Don't try to dump raw rows onto a slide.
2. **Plan slide-by-slide before calling the tool.** A good
   general-purpose structure (adapt to the request):
   - `cover` (title / subtitle / tagline)
   - `section` or `title` divider for each major section
   - **Vary the layout per slide.** Mix `kpi`, `content`, `two_column`,
     `chart`, `table`, `image_text`, `quote`. **Never produce three
     `content` slides in a row** — it's the #1 mark of a forgettable
     AI deck.
   - One `chart` or `table` for any meaningful comparison.
   - `conclusion` to close.
3. **Pick a content-informed theme.** Default to `"professional"`
   for business decks, `"modern"` for product/marketing,
   `"minimal"` for technical reviews. Use `"midnight_executive"`,
   `"terracotta"`, `"forest_moss"`, or a custom palette object when
   the topic calls for something more distinctive. **Don't default
   to blue for everything.**
4. **Call `pptx.create`** with `output=<same-dir-as-source>/<name>.pptx`
   and `page_numbers=true` for anything longer than ~5 slides.
5. **ALWAYS verify with `pptx.see`** after creation. This is not
   optional. Render at least the cover plus one content slide and one
   chart/table slide and look for:
   - Text that overflows or wraps badly (often longer than the layout
     expected).
   - Empty / placeholder areas (e.g. you passed `bullets` but the slide
     `type` was `image` so the bullets were ignored).
   - Wrong slide type for the content (long text on a `kpi` slide; one
     bullet on a `two_column` slide).
   - Low-contrast text (typically when a custom theme set `text` too
     close to `background`).

   If you see issues, fix them and re-render. **Do not declare the deck
   done until you've completed at least one render-and-fix cycle.**

#### Slide-type cheat sheet

- `cover` / `conclusion` — full-bleed primary background, one big line.
  Use exactly once each.
- `title` / `section` — divider slides. Use sparingly between major
  sections.
- `content` — title + paragraph + bullets. The workhorse, but don't
  overuse it.
- `two_column` — comparisons, before/after, pros/cons, dual lists.
- `kpi` — 2-6 headline numbers. Each item: `{label, value, delta?,
  color?}`.
- `table` — first row is automatically styled as the header. Keep
  ≤ ~8 rows per slide so it stays legible.
- `chart` — `kind`: `bar`/`column`/`barh`/`line`/`pie`/`doughnut`/
  `area`. Pass `labels` (categories) and `data` (array of series, each
  a list of numbers). Add `series_names` when you have more than one
  series.
- `image` — title + one big image (path must exist on disk).
- `image_text` — image on one side (`image_side: "left"|"right"`),
  body+bullets on the other. Great for "show + tell".
- `quote` — large pull-quote with attribution. Use once per deck at
  most.

#### Notes
- Each slide may carry `notes: "<speaker notes>"` — use them for
  detail that won't fit on the slide itself.
- Text fields take plain strings — `pptx.create` does not parse inline
  `<b>`/`<i>` markup. Bold/colour come from the theme and slide type.
- For numbers, format them yourself before passing them in
  (`"$1,234.56"`, `"12.4%"`); the tool does not auto-format.

#### `pptx.from_html_editable` — editable deck from arbitrary HTML

Use when the user wants edit-ability *and* a layout the
`pptx.create` DSL can't express cleanly (custom KPI cards, dashboard-
style grids, branded covers with gradients).

1. **Size each slide explicitly.** No `@page` rule needed — each
   `.slide` container is the slide. Standard 16:9:
   ```css
   .slide { width: 13.333in; height: 7.5in; padding: 0.75in;
            box-sizing: border-box; position: relative; }
   ```
2. **One `<section class="slide">` per slide.** Any element with class
   `slide` works; `<section>` is conventional.
3. **Stick to "well-supported" CSS** if you care about visual fidelity:
   solid + `linear-gradient` backgrounds, `border-radius`, padding,
   flex/grid, system fonts, `<table>`, `<img>`. **`box-shadow`,
   `filter`, `clip-path`, `radial-gradient`, `conic-gradient` are
   ignored** — if you need them, switch to `pptx.from_html`.
4. **System fonts only**, or accept that viewers without your web
   font installed will see a fallback. The browser renders with the
   web font correctly, but the PPTX records only the font *name*.
5. **Speaker notes** go through `notes=[...]` (one per slide, `null`
   to skip). Length must be ≤ slide count.
6. **`dependency_missing` on first call** = Playwright Chromium not
   installed. Tell the user to run `python -m playwright install
   chromium`; do not retry until then.
7. **Always verify with `pptx.see`** afterwards. The browser-to-PPTX
   round-trip can shift text bounding boxes slightly when the text
   re-flows in PowerPoint's text engine; check the cover, one busy
   content slide, and any table.

#### `pptx.from_html` — when design beats edit-ability

1. **Decide the slide size first.** The `@page` rule in your HTML
   sets it. 16:9 widescreen: `@page { size: 13.333in 7.5in; margin: 0 }`.
   Always `margin: 0` — paint your own padding inside `.slide` containers,
   otherwise WeasyPrint leaves a hairline white border around each slide.
2. **One container per slide.** Standard pattern: `.slide { width:
   13.333in; height: 7.5in; padding: 0.75in; box-sizing: border-box;
   page-break-after: always; display: flex; flex-direction: column; }`
   then `.slide:last-child { page-break-after: auto }`. That
   guarantees one HTML `<section class='slide'>` becomes exactly one
   slide.
3. **Lean into the design surface.** Web fonts (`<link rel="stylesheet"
   href="https://fonts.googleapis.com/...">`), gradients (`background:
   linear-gradient(...)` or `radial-gradient(...)`), CSS Grid for KPI
   rows, full-bleed cover backgrounds, exotic aspect ratios (1080×1080
   for social, 1080×1920 for stories). The full crash course is in
   `pdf.create`'s card — same engine.
4. **Speaker notes** go through the `notes=[...]` parameter (one per
   slide, in order, `null` to skip). Length must be ≤ `slide_count`.
5. **DPI defaults to 192** (Retina/projector-crisp). Bump to 300+ if
   the user explicitly needs print quality; drop to 96 for a fast
   preview deck.
6. **The deck is not editable.** Don't promise the user "and you can
   tweak the chart in PowerPoint" — every slide is a single Picture.
   If they're going to edit, switch to `pptx.create` upstream.

If the user already drafted an HTML report (e.g. via `html.create`)
and now wants it as a deck, just pass the file path as `html=` and
override the `@page` rule in the source to your slide size first.

### Converting a deck

- `pptx.convert(path=..., output=...pdf)` runs LibreOffice in
  headless mode and writes a PDF with one page per slide. Use this
  whenever the user asks to "export as PDF" or to feed the deck into
  a PDF-only downstream tool.
- The first conversion is slow (cold LibreOffice startup). Subsequent
  ones in the same process are faster but still measured in seconds.

### Forms / encryption

- PPTX has no equivalent of PDF form fields or encryption tools in
  this skill. If the user asks for that, tell them PowerPoint encrypts
  via the desktop app's file-password feature; this skill cannot
  encrypt or decrypt `.pptx` files.

## Conventions

- **Slide numbers are 1-based** in every tool's `slides` argument. The
  model output should also speak in 1-based numbers. Never write
  "index 0".
- **Slide spec syntax** is `"1"`, `"1-5"`, `"1,3,7-9"`. No spaces.
  `pptx.split` preserves the *order* given in the spec, so
  `slides="3,1,2"` reorders.
- **Never overwrite the user's input file.** Always write to a new
  `output` path. If the user explicitly asks to replace, pass
  `overwrite=true` but warn them once in the reply.
- **Output paths**: prefer the same directory as the input, with a
  suffix like `-merged.pptx`, `-pages-1-5.pptx`, `.pdf`. If the user
  did not specify, propose one and proceed.
- **Big decks**: if `slide_count > 30` and the user did not narrow,
  summarise the deck from the first few slides and the speaker notes
  before extracting everything.

## QA checklist (for `pptx.create`)

**Assume there are problems on first render. Your job is to find them.**

After every `pptx.create` call, run `pptx.see` on the cover plus one
or two interior slides and look for:

- Overlapping elements (text running through shapes, captions colliding
  with images).
- Text overflow or text cut off at the edge of a box.
- Decorative bars positioned for one-line titles but the title wrapped.
- Low-contrast text (e.g. light text on a near-white background, or
  dark text on the primary background of a `cover` slide).
- Empty placeholder areas (you supplied bullets but picked the wrong
  slide type).
- Monotonous layout sequence (three `content` slides in a row, or
  `kpi` then `kpi` then `kpi`).
- KPI cards crammed too tight (more than 5-6 cards on one slide).
- Tables with too many rows (> ~8) — the engine will shrink rows but
  the text gets unreadable.

If you find issues, fix them and re-render. **Do not declare success
on the first render alone.**

## Edge cases

- **`file_not_found`**: ask the user for a corrected path; do not list
  files or guess.
- **`unsupported_format`**: the file is not a `.pptx` or is corrupt.
  If the extension is `.pdf`/`.docx`/`.xlsx`, point them at the right
  skill.
- **`dependency_missing`** on `pptx.read`, `pptx.extract_text`, or
  `pptx.create`: the runtime is missing `python-pptx`. Tell the user
  and stop.
- **`dependency_missing`** on `pptx.convert` or `pptx.see`:
  LibreOffice (`soffice`) is not on `PATH` (and/or `pypdfium2` is
  absent for `see`). Tell the user; do not retry.
- **`slide_out_of_range`**: re-read with `pptx.read` to get the true
  slide count, then re-issue with a valid range.
- **`too_many_slides`** from `pptx.see`: split the request into ≤5-slide
  calls or ask which 5 slides matter most.
- **`split_failed`** / **`merge_failed`**: surface the underlying
  message and stop. These usually mean a deck has unusual XML that
  python-pptx couldn't clone — suggest the user export the source
  deck through PowerPoint or LibreOffice once to normalise it.
- **`timeout`** from `pptx.convert` or `pptx.see`: pass a higher
  `timeout_seconds` and retry once. If it still times out, the deck
  likely contains a problematic embed.

## References

- The Anthropic upstream `pptx` skill (in `anthropic-skills/skills/pptx/`)
  documents the underlying ecosystem (python-pptx, markitdown,
  pptxgenjs, LibreOffice + `pdftoppm`). This skill exposes the same
  capabilities — including deck authoring via `pptx.create` and visual
  inspection via `pptx.see` — as tool calls; do not shell out or write
  python-pptx scripts yourself.
- The colour palettes and the QA mindset ("assume there are problems")
  come from that upstream skill — read it for design inspiration when
  picking a theme or planning slide variety.
