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
