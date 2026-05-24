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
| `/`         | **Chat** — talk to the orchestrator. Sidebar toggles which specialists it can use. |
| `/runs`     | **Runs** — every live + persisted run with full audit drill-down.                 |
| `/packs`    | **Packs** — catalog with skills, tools, limits, classification.                   |
| `/skills`   | **Skills** — catalog with SKILL.md body + required tools.                         |
| `/tools`    | **Tools** — catalog with tool card + JSON schema, filterable by tag.              |
| `/evals`    | **Evals** — case browser, runner with live streaming, results history.            |

### How the chat works

The user never picks a pack. Every message goes to the **router** pack —
a meta-agent whose only tools are `orchestrator.list_packs` and
`orchestrator.delegate`. The router reads the message, decides whether
it needs a specialist, picks one from the allowed list, and delegates a
self-contained sub-task. The specialist runs as a nested sub-agent in
the same worker process; its events are forwarded to the UI tagged with
`subagent_of: <pack>` and shown indented under the parent `delegate` call.

The sidebar checklist controls `allowed_packs` per request. Unchecked
packs are invisible to the orchestrator.

## How it streams

The supervisor is synchronous and writes audit JSONL. The server wraps it
with an `on_event` callback that pushes into per-subscriber `asyncio.Queue`s
behind an SSE endpoint. The frontend uses native `EventSource` to subscribe.

```
POST /api/runs          { user_message, allowed_packs? } → { run_id }
  (escape hatch: pass { pack: "hello", user_message } to skip the router)
GET  /api/runs/:id/stream  SSE: skill_activated, tool_call, tool_result,
                               model_text, error, done
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

## Stack notes

- **Vite + React + TS.** `vite.config.ts` proxies `/api` to the backend.
- **Tailwind v4** (CSS-only config) via `@tailwindcss/vite`.
- **shadcn/ui** components, added with the CLI (`npx shadcn add ...`).
- **react-router-dom** for client routing.
- **sonner** for toast notifications.
- **lucide-react** for icons.

No state library, no react-query — `fetch` + `useEffect`. If the app grows
beyond what that supports cleanly, add react-query.
