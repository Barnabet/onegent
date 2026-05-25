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
