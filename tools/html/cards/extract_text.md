---
tool: html.extract_text
version: 1
owner: team-doc-ai
classification: [internal]
tags: [html, read, text]
---

# html.extract_text

## Purpose
Extract the readable text content of an HTML file. Strips `<script>`,
`<style>`, and template/noscript blocks; preserves block-level
structure with line breaks; collapses whitespace. Image `alt` text is
rendered inline as `[image: <alt>]` so it isn't lost.

## When to use
- The user asks "what does this HTML say" / "summarise this page".
- A skill needs the body text to feed into summarisation, translation,
  or comparison.
- You want to re-flow an HTML report's content into a different format
  (e.g. an email).

## When NOT to use
- For element counts or metadata — use `html.read` (cheaper).
- For visual layout, charts, or rendered styles — use `html.see`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.html` / `.htm` file. |
| max_chars | int | no | Cap on returned text. Result is truncated and `truncated=true` set when hit. Default 50000. Pass 0 to disable. |

## Returns
```
{
  ok: true,
  data: {
    title: <str|null>,
    text: <str>,
    char_count: <int>,
    truncated: <bool>
  }
}
```

## Errors
- `file_not_found` / `unsupported_format` — bad input.
- `parse_failed` — HTML parse error.

## Examples
### Full body
Call: `html.extract_text(path="/tmp/audit.html")`

### Quick first page
Call: `html.extract_text(path="/tmp/long-report.html", max_chars=4000)`

## See also
- `html.read` — title and counts only.
- `html.see` — image render when layout matters.
