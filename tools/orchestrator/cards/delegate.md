---
tool: orchestrator.delegate
version: 1
owner: team-platform-ai
classification: [public]
tags: [routing, meta]
---

# orchestrator.delegate

## Purpose
Hand off a self-contained sub-task to a specialist pack. The specialist
runs in a fresh sub-agent loop with its own skills and tools, then
returns its final text reply and a summary of what it did.

## When to use
- The user's request maps to a single specialist pack from
  `orchestrator.list_packs`. Pick the best one and delegate.
- The user's request needs multiple specialists. Delegate to each one in
  turn with the relevant sub-task; combine their answers yourself.

## When NOT to use
- For pure conversational replies ("hi", "what can you do?") — answer
  yourself. Do not delegate trivia.
- To call a pack that is not in the allowed list — the call will fail
  with `pack_not_allowed`.
- To pass the user's raw message verbatim when it contains context the
  specialist does not need. Rewrite the sub-task to be self-contained.

## Parameters
| name | type | required | description |
|---|---|---|---|
| pack | string | yes | The pack name to delegate to. Must be in `allowed_packs`. |
| message | string | yes | A self-contained sub-task for the specialist. Include all context it needs — it cannot see the parent conversation. |

## Returns
On success: `{ok: true, data: {pack, final_text, stats: {turns, tool_calls, finish_reason}}}`

`final_text` is the specialist's last reply. Quote it or summarise it for
the user. The full event stream from the sub-agent is also forwarded
into the parent run's audit log automatically — you do not need to
re-emit it.

## Errors
- `pack_not_allowed` — `pack` is not in the router's `allowed_packs`.
- `pack_not_found` — `pack` does not exist.
- `subagent_failed` — the specialist raised; `error.message` has detail.

## Examples
### Routing a credit memo request
Call: `orchestrator.delegate(pack="credit_analyst", message="Draft a credit memo for Acme SpA. Financials: /tmp/acme.xlsx")`
Returns: `{ok: true, data: {pack: "credit_analyst", final_text: "Memo drafted...", stats: {turns: 4, tool_calls: 3, finish_reason: "stop"}}}`

### Smoke-test
Call: `orchestrator.delegate(pack="hello", message="ping")`
Returns: `{ok: true, data: {pack: "hello", final_text: "Platform is alive...", stats: {...}}}`

## See also
- `orchestrator.list_packs` — see which packs are available first.
