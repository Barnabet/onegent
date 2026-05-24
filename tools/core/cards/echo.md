---
tool: core.echo
version: 1
owner: team-platform-ai
classification: [public]
tags: [diagnostic, smoke-test]
---

# core.echo

## Purpose
Return the input string unchanged. Used only for smoke-tests of the agent
loop and tool plumbing.

## When to use
- The user asks you to "echo" a specific string back to them verbatim.
- A skill explicitly instructs you to call `core.echo` as a connectivity check.

## When NOT to use
- For any real task. This tool does no useful work.
- To repeat the user's message back in a conversational reply — just include
  the text in your own response, no tool call needed.

## Parameters
| name | type | required | description |
|---|---|---|---|
| text | string | yes | The exact string to echo back. Keep it short (< 200 chars). |

## Returns
On success: `{ok: true, data: {echoed: "<text>"}}`

## Errors
- `invalid_input` — `text` missing or not a string.

## Examples
### Smoke-test call
Call: `core.echo(text="hello")`
Returns: `{ok: true, data: {echoed: "hello"}}`

## See also
- (none — this tool exists in isolation for diagnostics.)
