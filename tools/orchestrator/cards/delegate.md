---
tool: orchestrator.delegate
version: 2
owner: team-platform-ai
classification: [public]
tags: [routing, meta]
---

# orchestrator.delegate

## Purpose
Spawn a sub-agent to handle a self-contained sub-task. The sub-agent runs
in a fresh loop with its own skills and tools, then returns its final
text reply and a summary of what it did.

Three shapes are supported:

1. **Pack** — `pack="credit_analyst"`. The specialist runs with the
   pack's own skills. Use when a specialist already matches the task.
2. **Pack + extra skills** — `pack="credit_analyst", extra_skills=["pdf_handling"]`.
   Splice extra skills (from `orchestrator.list_skills`) on top of the
   pack's skills. Use when a specialist is *almost* right but needs one
   more capability for this task.
3. **Skills only** — `skills=["pdf_handling", "xlsx_handling"]`, no `pack`.
   Ad-hoc sub-agent composed from individual skills, running under the
   router's own model / classification / limits. Use when no specialist
   fits but a combination of skills will.

## When to use
- The user's request maps to a single specialist pack from
  `orchestrator.list_packs`. Pick it and delegate.
- The user's request needs multiple specialists. Delegate to each one in
  turn and combine the answers yourself.
- The user's request needs a capability mix that no specialist provides.
  Compose it from `orchestrator.list_skills` using `skills=[...]`.

## When NOT to use
- For pure conversational replies ("hi", "what can you do?") — answer
  yourself. Do not delegate trivia.
- To call a pack outside `allowed_packs` — the call fails with
  `pack_not_allowed`. (Skills are not gated; pick any from
  `orchestrator.list_skills`.)

## Parameters
| name | type | required | description |
|---|---|---|---|
| pack | string | one-of | Specialist pack name. Must be in `allowed_packs`. |
| skills | string[] | one-of | Skills for an ad-hoc sub-agent (no pack). Pick from `orchestrator.list_skills`. |
| extra_skills | string[] | no | Extra skills to add on top of `pack`. Pick from `orchestrator.list_skills`. Ignored without `pack`. |
| message | string | yes | Self-contained sub-task. Include all context — the sub-agent cannot see the parent conversation. |
| files | string[] | no | Conversation `file_id`s to forward. Omit/`null` = all attachments (default). `[]` = none. Subset = only those. Unknown ids are dropped. |

Exactly one of `pack` or `skills` must be set.

## Returns
On success: `{ok: true, data: {pack, skills, final_text, stats: {turns, tool_calls, finish_reason}}}`

`pack` is `null` for skills-only sub-agents. `skills` is the resolved
skill list actually bound on the sub-agent. `final_text` is the
sub-agent's last reply — quote it or summarise it for the user. The full
event stream is forwarded into the parent run's audit log automatically.

## Errors
- `invalid_input` — neither/both of `pack`/`skills` set, or `extra_skills`
  passed without `pack`.
- `pack_not_allowed` — `pack` not in `allowed_packs`.
- `pack_not_found` — `pack` does not exist on disk.
- `skill_not_found` / `skills_bind_failed` — a requested skill could not
  be loaded or its tools/classification could not be bound.
- `subagent_failed` — the sub-agent raised; `error.message` has detail.

## Examples
### Routing a credit memo request
Call: `orchestrator.delegate(pack="credit_analyst", message="Draft a credit memo for Acme SpA. Financials: /tmp/acme.xlsx")`
Returns: `{ok: true, data: {pack: "credit_analyst", skills: [...], final_text: "Memo drafted...", stats: {turns: 4, tool_calls: 3, finish_reason: "stop"}}}`

### Topping up a specialist with PDF reading
Call: `orchestrator.delegate(pack="credit_analyst", extra_skills=["pdf_handling"], message="...", files=["f_kbis"])`

### Skills-only ad-hoc sub-agent
Call: `orchestrator.delegate(skills=["pdf_handling", "xlsx_handling"], message="Cross-check the totals in /tmp/a.pdf against /tmp/b.xlsx", files=["f_pdf", "f_xlsx"])`
Returns: `{ok: true, data: {pack: null, skills: ["pdf_handling", "xlsx_handling"], final_text: "...", stats: {...}}}`

## See also
- `orchestrator.list_packs` — see which specialist packs are available.
- `orchestrator.list_skills` — see which skills you may compose.
