---
tool: orchestrator.list_skills
version: 1
owner: team-platform-ai
classification: [public]
tags: [routing, meta]
---

# orchestrator.list_skills

## Purpose
List every skill installed on disk. These are the skills the orchestrator
may compose into a sub-agent via `orchestrator.delegate` — either as
`skills=[...]` (ad-hoc sub-agent) or `extra_skills=[...]` (added on top
of a pack).

This is **not** the same as the skills the orchestrator may invoke
*itself*. The orchestrator's own callable skills are fixed by the router
pack definition (`packs/router.yaml: skills:`) and are surfaced to the
model as the tool list it already has access to.

## When to use
- Before composing a skills-only sub-agent, to see what's available.
- When deciding whether to top up a `pack` delegation with `extra_skills`.

## When NOT to use
- If you have already called this in the current turn — the list does not
  change mid-run. Cache the answer.

## Parameters
(none)

## Returns
On success: `{ok: true, data: {skills: [{name, description}, ...]}}`

## Errors
- `no_router_context` — this tool was called outside a router run.
  Should not happen in practice.

## Examples
### Discovering composable skills
Call: `orchestrator.list_skills()`
Returns: `{ok: true, data: {skills: [
  {name: "pdf_handling", description: "Read and inspect PDF files."},
  {name: "xlsx_handling", description: "Inspect, query (SQL), read, write, edit, format, recalculate, and convert spreadsheets."},
  {name: "router", description: "Routing rules for the orchestrator."}
]}}`

## See also
- `orchestrator.delegate` — compose and invoke a sub-agent.
- `orchestrator.list_packs` — see pre-defined specialist packs.
