# Web UI

A React + shadcn frontend for interactive testing of agents, plus a
FastAPI backend that exposes the supervisor and eval harness over HTTP.

## Running

Two terminals:

```bash
# 1. Backend
python scripts/serve.py
# → uvicorn on http://127.0.0.1:8000

# 2. Frontend (first time: `npm install`)
cd webui && npm run dev
# → Vite on http://localhost:5173 (proxies /api → :8000)
```

Open <http://localhost:5173>.

## Pages

The chat is the primary view. Everything else is a catalog or audit page
behind the **More** dropdown in the header.

| Route       | What it does                                                                       |
| ----------- | ---------------------------------------------------------------------------------- |
| `/`         | **Chat** — talk to the orchestrator. Left sidebar lists / manages conversations; right sidebar holds the active conversation's files. |
| `/runs`     | **Runs** — every live + persisted run with full audit drill-down.                 |
| `/packs`    | **Packs** — catalog with skills, tools, limits, classification.                   |
| `/skills`   | **Skills** — catalog with SKILL.md body + required tools.                         |
| `/tools`    | **Tools** — catalog with tool card + JSON schema, filterable by tag.              |
| `/evals`    | **Evals** — case browser, runner with live streaming, results history.            |

### How the chat works

The user never picks a pack. Every message goes to the **router** pack —
a meta-agent whose only routing tool is `orchestrator.delegate`. The
router's system prompt inlines the catalog of delegatable packs and the
catalog of composable skills, so the router can pick a target natively
without any extra tool calls. It reads the message, decides whether it
needs a specialist, and spawns a sub-agent in one of three shapes: a
pack, a pack plus extra skills, or an ad-hoc combo of skills with no
pack. Sub-agent events are forwarded to the UI tagged with
`subagent_of: <label>` and shown indented under the parent `delegate`
call.

Conversations are server-side and persisted (one JSON per conversation
under `conversations/`). Each `POST /api/runs` carries a
`conversation_id`; the server loads the prior `(user, assistant)`
transcript and passes it as `history` to the worker, then appends the
new turn on completion. Sub-agents get no history — each delegation is
self-contained. Files are attached to the conversation, not the run, so
they persist across turns and across server restarts.

## How it streams

The supervisor is synchronous and writes audit JSONL. The server wraps it
with an `on_event` callback that pushes into per-subscriber `asyncio.Queue`s
behind an SSE endpoint. The frontend uses native `EventSource` to subscribe.

```
POST /api/runs          { user_message, conversation_id, allowed_packs? } → { run_id }
  (escape hatch: pass { pack: "hello", user_message } to skip the router)
GET  /api/runs/:id/stream  SSE: tool_call, tool_result, model_text, error, done
GET  /api/runs/:id      Final RunResult (after done)
```

Eval jobs work the same way: `POST /api/evals/run` → SSE stream of
`case_done` events → final summary on `done`.

## API map

| Endpoint                          | Method | Purpose                          |
| --------------------------------- | ------ | -------------------------------- |
| `/api/health`                     | GET    | Liveness + tool count            |
| `/api/tools`                      | GET    | List tools (summary)             |
| `/api/tools/:name`                | GET    | Tool card + JSON schema          |
| `/api/skills`                     | GET    | List skills (frontmatter)        |
| `/api/skills/:name`               | GET    | Body + manifest                  |
| `/api/packs`                      | GET    | List packs                       |
| `/api/packs/:name`                | GET    | Bound pack (skills + tools)      |
| `/api/runs`                       | POST   | Start a supervisor run           |
| `/api/runs`                       | GET    | All live + persisted runs        |
| `/api/runs/:id`                   | GET    | Full run + events                |
| `/api/runs/:id/stream`            | GET    | SSE event stream                 |
| `/api/evals/cases`                | GET    | List eval cases                  |
| `/api/evals/run`                  | POST   | Start an eval job                |
| `/api/evals/jobs/:id/stream`      | GET    | SSE: per-case results            |
| `/api/evals/results`              | GET    | Past `evals/results/*.jsonl`     |
| `/api/conversations`              | GET    | List conversations (summary)     |
| `/api/conversations`              | POST   | Create a conversation            |
| `/api/conversations/:id`          | GET    | Full conversation + files        |
| `/api/conversations/:id`          | PATCH  | Rename                           |
| `/api/conversations/:id`          | DELETE | Delete + remove attached files   |

## Stack notes

- **Vite + React + TS.** `vite.config.ts` proxies `/api` to the backend.
- **Tailwind v4** (CSS-only config) via `@tailwindcss/vite`.
- **shadcn/ui** components, added with the CLI (`npx shadcn add ...`).
- **react-router-dom** for client routing.
- **sonner** for toast notifications.
- **lucide-react** for icons.

No state library, no react-query — `fetch` + `useEffect`. If the app grows
beyond what that supports cleanly, add react-query.
