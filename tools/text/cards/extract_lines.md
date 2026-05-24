---
tool: text.extract_lines
version: 1
owner: team-platform-ai
classification: [public]
tags: [text, extract, numeric, deterministic]
---

# text.extract_lines

## Purpose
Scan a text and return the subset of lines that contain numbers, percentages,
currency amounts, or `Key: value` patterns. Deterministic, no LLM. The
returned lines are the raw material a skill can summarize or cite.

## When to use
- A skill is processing a free-form document (credit input, KYC dossier,
  research note) and needs to surface the quantitative / structured lines.
- Before drafting a summary, to give the model a ranked candidate set of
  lines worth quoting verbatim.

## When NOT to use
- For producing a prose summary — the skill itself should do that using
  the lines this tool returns. There is no LLM-summarization tool by design.
- For parsing structured spreadsheets — use `xlsx.read`.
- For extracting tables out of a PDF — use `pdf.extract_tables` (when
  available).

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The text to scan. |
| kinds | list[string] | no | Subset of `numeric`, `percentage`, `currency`, `key_value`. Default: all four. |

## Returns
On success:
```
{
  ok: true,
  data: {
    lines: [
      {line_no: 4, text: "Revenue: EUR 412m (+8.2% YoY)", kinds: ["numeric","percentage","currency","key_value"]},
      ...
    ],
    total_matched: 7
  }
}
```

## Errors
- `empty_input` — the text was empty or whitespace-only.

## Examples
### Surface numeric lines from a credit file
Call: `text.extract_lines(text="<credit file body>")`
Returns: `{ok: true, data: {lines: [{line_no: 4, text: "Revenue: EUR 412m ...", kinds: [...]}, ...], total_matched: 6}}`

### Only key:value lines
Call: `text.extract_lines(text="...", kinds=["key_value"])`

## See also
- `text.word_count` — basic metrics.
- `xlsx.read` — when the source is tabular, not prose.
