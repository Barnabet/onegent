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
