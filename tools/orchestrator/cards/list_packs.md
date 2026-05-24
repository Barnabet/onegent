---
tool: orchestrator.list_packs
version: 1
owner: team-platform-ai
classification: [public]
tags: [routing, meta]
---

# orchestrator.list_packs

## Purpose
List the specialist packs the router is allowed to delegate to. Returns
each pack's name + one-line description so the model can pick the right
one for a user request.

## When to use
- At the start of a router run, to see what specialists are available.
- When the user asks a new question and you need to decide which
  specialist (if any) should handle it.

## When NOT to use
- If you have already called this in the current turn — the list does not
  change mid-run. Cache the answer.
- For pure conversational replies that do not need a specialist.

## Parameters
(none)

## Returns
On success: `{ok: true, data: {packs: [{name, description, classification}, ...]}}`

## Errors
- `no_router_context` — this tool was called outside a router run
  (no `allowed_packs` configured). Should not happen in practice.

## Examples
### Discovering specialists
Call: `orchestrator.list_packs()`
Returns: `{ok: true, data: {packs: [
  {name: "credit_analyst", description: "Pilot pack for credit analysts...", classification: "confidential"},
  {name: "hello", description: "Smoke-test pack...", classification: "public"}
]}}`

## See also
- `orchestrator.delegate` — actually invoke a specialist with a sub-task.
