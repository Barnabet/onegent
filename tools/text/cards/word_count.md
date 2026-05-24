---
tool: text.word_count
version: 1
owner: team-platform-ai
classification: [public]
tags: [text, metrics, deterministic]
---

# text.word_count

## Purpose
Return the number of words and characters in a piece of text.

## When to use
- A skill needs to check whether a draft fits a length budget before
  returning it.
- Quick sanity check on a document's size before deciding whether to chunk it.

## When NOT to use
- For token counting against a specific model — this tool returns word
  count, not tokens.
- For extracting structured content — use `text.extract_lines`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The text to measure. |

## Returns
On success: `{ok: true, data: {words: <int>, chars: <int>}}`

## Errors
_(none)_

## Examples
### Measure a draft
Call: `text.word_count(text="...")`
Returns: `{ok: true, data: {words: 412, chars: 2890}}`

## See also
- `text.extract_lines` — for content-level extraction.
