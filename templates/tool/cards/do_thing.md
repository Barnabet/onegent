---
tool: example.do_thing
version: 1
owner: team-replace-me
classification: [internal]
tags: [example, replace-me]
---

# example.do_thing

## Purpose
One sentence. What it does, not how.

## When to use
- Specific trigger situations, in the model's voice.
- e.g. "The user provides X and asks to Y."

## When NOT to use
- Near-miss situations that should go elsewhere — and link the alternative.
- e.g. "For Z, use `other.tool` — it handles Q better."
- (This section is the most important one. If it is empty, your tool will be
  rejected in review. If you cannot name an adjacent tool, your tool is
  either too generic or duplicates something that already exists.)

## Parameters
| name | type | required | description |
|---|---|---|---|
| target | string | yes | Semantic description, not just the type. |
| option | string | no  | Document allowed values and defaults. |

## Returns
On success: `{ok: true, data: {result: <shape>}}`

## Errors
- `not_found` — describe when this fires.
- `invalid_input` — describe when this fires.

## Examples
### Basic call
Call: `example.do_thing(target="...")`
Returns: `{ok: true, data: {result: "..."}}`

### With option
Call: `example.do_thing(target="...", option="...")`

## See also
- `<other.tool>` — when to prefer it.
