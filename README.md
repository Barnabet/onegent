# onegent

A skills × tools library for building Gen-AI agents. Thin orchestrator,
shared tool catalog, file-based skills and packs — no LangChain, no DSL.

<p align="center">
  <img src="logo.png" width="160" alt="onegent" />
</p>

## What it is

Five concepts. Learn these and the rest is mechanical:

| Concept | What it is | Lives in |
|---|---|---|
| **Tool** | A deterministic Python function the model can call. | `tools/<domain>/impl.py` |
| **Tool card** | Markdown telling the model when/how to use the tool. | `tools/<domain>/cards/*.md` |
| **Skill** | A playbook for a class of tasks. References tools by name. | `skills/<skill>/SKILL.md` |
| **Pack** | A curated bundle of skills for a persona, with limits + risk review. | `packs/*.yaml` |
| **Sub-agent** | A worker process the supervisor spawns with exactly one pack loaded. | `orchestrator/` |

The two rules that make it compound:

1. **Tools are shared.** They live in `tools/<domain>/`, not in skill folders. Any skill can declare any tool.
2. **No shell, no install.** Skills only ever ask the model to call registered tools by name.

## Quick start

```bash
pip install -r requirements.txt
python -m playwright install chromium   # only if you use pptx.from_html_editable
python -m pytest                        # 201 tests

# CLI — one-shot run
python scripts/run.py --pack hello "ping"

# Eval harness
python scripts/eval.py [--pack X] [--case Y] [--no-judge]

# Web UI (two terminals)
python scripts/serve.py                       # FastAPI on :8000
cd webui && npm install && npm run dev        # Vite on :5173 (proxies /api)
```

Then open <http://localhost:5173> for chat, run history, catalogs, and the eval dashboard.

The LLM is reached over an OpenAI-compatible HTTP endpoint configured in
`runtime/llm.py` (defaults to a local CLIProxyAPI at `http://127.0.0.1:8317/v1`).

## What ships

**Tool domains** (`tools/<domain>/`):

| Domain | Tools |
|---|---|
| `core` | `echo` |
| `repo` | `read_doc`, `read_catalog`, `search_catalog`, `scaffold_tool`, `scaffold_skill`, `scaffold_pack` |
| `docstore` | `fetch` (mock-backed by `fixtures/docstore/`) |
| `text` | `extract_lines`, `word_count` |
| `xlsx` | `info`, `read`, `sql`, `write`, `edit_cells`, `format`, `convert`, `recalc` |
| `pdf` | `read`, `extract_text`, `extract_tables`, `see`, `ocr`, `merge`, `split`, `rotate`, `encrypt`, `decrypt`, `form_fields`, `fill_form`, `create` |
| `pptx` | `read`, `see`, `extract_text`, `extract_notes`, `merge`, `split`, `convert`, `create`, `from_html`, `from_html_editable` |
| `html` | `create`, `read`, `see`, `extract_text`, `to_pdf` |
| `orchestrator` | `delegate` |

**Skills** (`skills/<skill>/`): `hello`, `router`, `xlsx_handling`,
`pdf_handling`, `pptx_handling`, `html_reporting`, `credit_memo`,
`skill_creator`.

**Packs** (`packs/*.yaml`):

| Pack | Skills |
|---|---|
| `hello` | `hello` |
| `router` | `router` + `pdf_handling` + `xlsx_handling` + `pptx_handling` + `html_reporting` (user-facing entry point; delegates real work) |
| `credit_analyst` | `xlsx_handling` + `credit_memo` |
| `skill_creator` | `skill_creator` |

## Start here

1. **`docs/concepts.md`** — the five concepts and how they fit together (~5 min).
2. **`docs/example-kyc-screening.md`** — canonical worked example, end to end.
3. **`docs/authoring-tools.md`** — how to add a tool.
4. **`docs/authoring-skills.md`** — how to write a skill.
5. **`docs/authoring-packs.md`** — how to bundle skills into a pack.
6. **`docs/evals.md`**, **`docs/webui.md`** — harness and UI.

## Layout

```
onegent/
├── tools/          # by domain — impl.py + registry.py + cards/*.md + tests/
├── skills/         # SKILL.md + manifest.yaml per skill
├── packs/          # one YAML per persona
├── orchestrator/   # supervisor + worker_entry + delegate
├── runtime/        # tool_registry, skill_loader, pack_loader, llm, audit, catalog_gen
├── evals/          # YAML cases, scoring, LLM-judge, runner, reports
├── server/         # FastAPI app (HTTP + SSE)
├── webui/          # Vite + React + shadcn (chat, runs, catalogs, evals)
├── scripts/        # run.py, eval.py, serve.py, check_catalog.py
├── docs/           # authoring guides + generated catalogs
├── templates/      # copy-paste skeletons for new tools / skills / packs
├── fixtures/       # mock data for pilots
└── tests/          # cross-cutting + end-to-end + eval harness
```

## Design decisions

- **Language**: Python 3.9+.
- **LLM**: OpenAI-compatible HTTP, swappable behind `runtime/llm.py`.
- **Skills + packs**: in-repo, PR-reviewed.
- **Sub-agents**: separate worker processes (one per request, via `multiprocessing`).
- **No LangChain / LangGraph.** Thin core, ~one file per concern.
