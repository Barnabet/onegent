# CIB Agents Library

A Skills × Tools library for building Gen AI agents at the bank.

## Status

**PR #5 — server + webui landed.** Three packs, four skills, four tool
domains, eval harness, FastAPI backend, and a React/shadcn web UI for
running and inspecting agents interactively.

```
pip install -r requirements.txt
python -m pytest                                  # 42 passed, 3 skipped (templates)

# CLI — one-shot run
python scripts/run.py --pack hello "ping"

# CLI — eval harness
python scripts/eval.py [--pack X] [--case Y] [--no-judge]

# Web UI (two terminals)
python scripts/serve.py                           # FastAPI on :8000
cd webui && npm install && npm run dev            # Vite on :5173 (proxies /api to :8000)
```

Open <http://localhost:5173> for the chat UI, run history, catalogs, and
eval dashboard.

### What ships (capabilities)

| Domain | Tools |
|---|---|
| `core` | `echo` |
| `repo` | `read_doc`, `read_catalog`, `search_catalog`, `scaffold_tool`, `scaffold_skill`, `scaffold_pack` |
| `docstore` | `fetch` (mock-backed by `fixtures/docstore/`) |
| `text` | `extract_lines`, `word_count` |
| `xlsx` | `read` (xlsx/xlsm/csv/tsv) |

| Skill | Tools used | Shared with |
|---|---|---|
| `hello` | `core.echo` | — |
| `xlsx_handling` | `xlsx.info`, `xlsx.read`, `xlsx.sql`, `xlsx.write`, `xlsx.edit_cells`, `xlsx.format`, `xlsx.convert`, `xlsx.recalc` | reused by `credit_memo` |
| `credit_memo` | `docstore.fetch`, `xlsx.read`, `text.extract_lines`, `text.word_count` | reuses xlsx_handling's tools |
| `skill_creator` | all `repo.*` tools | — (bootstrap) |

| Pack | Skills |
|---|---|
| `hello` | `hello` |
| `credit_analyst` | `xlsx_handling` + `credit_memo` |
| `skill_creator` | `skill_creator` |

## Start here

1. **`docs/concepts.md`** — the five concepts (tool, tool card, skill, pack, sub-agent) and how they fit together. ~5 min read.
2. **`docs/example-kyc-screening.md`** — the canonical worked example, end to end. Read this before authoring anything.
3. **`docs/authoring-tools.md`** — how to add a tool.
4. **`docs/authoring-skills.md`** — how to write a skill.
5. **`docs/authoring-packs.md`** — how to bundle skills into a pack.

## Layout

```
cib-agents/
├── docs/                # authoring guides + generated catalogs (later)
├── templates/           # copy-paste skeletons for new tools / skills / packs
│   ├── tool/
│   ├── skill/
│   └── pack/
├── tools/               # by domain — core, repo, docstore, text, xlsx
├── skills/              # hello, xlsx_handling, credit_memo, skill_creator
├── packs/               # hello, credit_analyst, skill_creator
├── fixtures/            # docstore mock data for the pilots
├── orchestrator/        # supervisor.py + worker_entry.py + subagent.py
├── runtime/             # tool_registry, skill_loader, pack_loader, llm, audit, catalog_gen
├── evals/               # YAML cases, scoring engine, LLM-judge, runner, reports
├── server/              # FastAPI app (HTTP + SSE) in front of the supervisor + evals
├── webui/               # Vite + React + shadcn UI (chat, runs, catalogs, evals)
├── scripts/             # run.py, eval.py, serve.py, check_catalog.py
└── tests/               # unit + spine end-to-end + eval harness
```

## The two rules that make it compound

1. **Tools are shared.** They live in `tools/<domain>/`, not in skill folders. Any skill can declare any tool.
2. **No shell, no install.** Skills only ever ask the model to call registered tools by name.

Everything else falls out of these two rules.

## Decisions locked

- **Language**: Python (target: whatever the local `python` runs — currently 3.9.13).
- **LLM**: OpenAI-compatible HTTP via local **CLIProxyAPI** at `http://127.0.0.1:8317/v1`. Swappable behind `runtime/llm.py`.
- **Skills + packs**: in-repo, PR-reviewed.
- **Sub-agents**: separate worker processes (one per request, via `multiprocessing`).
- **No LangChain / LangGraph.** Thin core, ~one file per concern.
