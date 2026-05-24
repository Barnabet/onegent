# CIB Agents Library

A Skills × Tools library for building Gen AI agents at the bank.

## Status

**PR #3 — reuse-proof + bootstrap landed.** Three packs, four skills, four
tool domains, all end-to-end verified against local CLIProxyAPI.

```
pip install -r requirements.txt
python -m pytest                                  # 28 passed, 3 skipped (templates)

# Smoke test
python scripts/run.py --pack hello "ping"

# Credit pilot — demonstrates tool reuse across xlsx_analysis + credit_memo
python scripts/run.py --pack credit_analyst \
  "Draft a credit memo for Acme Italia SpA. Financials: /tmp/acme_financials.xlsx"

# Bootstrap — the agent helps you write new skills/tools/packs
python scripts/run.py --pack skill_creator \
  "I want to create a new skill called pep_screen for PEP screening..."

python scripts/check_catalog.py --write           # regenerate docs/{tool,skill}-catalog.md
```

### What ships in PR #3

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
| `xlsx_analysis` | `xlsx.read`, `text.word_count` | reused by `credit_memo` |
| `credit_memo` | `docstore.fetch`, `xlsx.read`, `text.extract_lines`, `text.word_count` | reuses xlsx_analysis's tools |
| `skill_creator` | all `repo.*` tools | — (bootstrap) |

| Pack | Skills |
|---|---|
| `hello` | `hello` |
| `credit_analyst` | `xlsx_analysis` + `credit_memo` |
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
├── skills/              # hello, xlsx_analysis, credit_memo, skill_creator
├── packs/               # hello, credit_analyst, skill_creator
├── fixtures/            # docstore mock data for the pilots
├── orchestrator/        # supervisor.py + worker_entry.py + subagent.py
├── runtime/             # tool_registry, skill_loader, pack_loader, llm, audit, catalog_gen
├── scripts/             # run.py, check_catalog.py (scaffolding done via skill_creator)
└── tests/               # unit + spine end-to-end
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
