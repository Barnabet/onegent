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
