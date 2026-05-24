# Concepts

The library has five concepts. Learn these five and the rest of the docs make sense.

## The five things

| Concept | What it is | Lives in | Who writes it |
|---|---|---|---|
| **Tool** | A Python function the agent can call. Deterministic, server-side, no shell. | `tools/<domain>/` | Tool owner team |
| **Tool card** | A markdown doc telling the model when/how to use a tool. | `tools/<domain>/cards/*.md` | Tool author |
| **Skill** | A playbook telling the model how to accomplish a class of tasks, using tools. | `skills/<skill>/` | Skill author (often a finance SME + engineer) |
| **Pack** | A curated bundle of skills for a persona (e.g. credit analyst). | `packs/*.yaml` | Pack owner + risk review |
| **Sub-agent** | A worker process spawned by the supervisor with exactly one pack's skills + tools loaded. | `orchestrator/` | Framework — you don't write these |

## How they fit together

```
                       user request
                            │
                            ▼
                  ┌──────────────────┐
                  │   Supervisor     │   (parent process)
                  │   router → pack  │
                  └────────┬─────────┘
                           │ spawn worker (separate process)
                           ▼
              ┌────────────────────────────┐
              │        Sub-agent           │
              │  ┌──────────────────────┐  │
              │  │ Loaded skills (N)    │  │   ← from pack.yaml
              │  │  • SKILL.md          │  │
              │  │  • manifest.yaml     │  │
              │  └──────────┬───────────┘  │
              │             │ declares     │
              │             ▼              │
              │  ┌──────────────────────┐  │
              │  │ Bound tools (M)      │  │   ← union of all
              │  │  • function          │  │     skills' manifests
              │  │  • JSON schema       │  │
              │  │  • tool card (desc)  │  │
              │  └──────────────────────┘  │
              │             │              │
              │             ▼              │
              │       model loop           │
              │   (chat → tool_call →      │
              │    execute → repeat)       │
              └─────────────┬──────────────┘
                            │ events: tool_call, tool_result,
                            │         model_text, done
                            ▼
                       audit log + reply
```

## The two rules that make the library compound

### Rule 1 — Tools are shared, not owned by skills
A tool lives in `tools/<domain>/`, **never** in `tools/<skill_name>/`. Any skill can declare any tool in its `manifest.yaml`. Before writing a tool, you check the catalog. Before writing a skill, you pick tools from the catalog.

If you find yourself writing `tools/credit_memo/...`, stop. Ask: what *domain* does this tool actually belong to? `docstore`? `xlsx`? `text`? That's where it goes.

### Rule 2 — No shell, no install, no terminal
A skill never tells the model "run `pip install pypdf`" or "execute `python scripts/x.py`". It tells the model "call `pdf.extract_text`". Tools are pre-deployed, server-side Python. The agent only sees tool calls.

This is the single biggest departure from Anthropic's reference skills, and it's non-negotiable for our CIB environment.

## The execution model

1. User sends a request to the supervisor.
2. Supervisor's **router** picks a pack (static mapping or LLM classification — we start with static).
3. Supervisor spawns a **worker process** (`multiprocessing.Process`).
4. Worker loads the pack: parses every skill's `SKILL.md` + `manifest.yaml`, builds the union of required tools, binds them.
5. Worker runs the **model loop**: send messages + tools to the LLM, execute any `tool_call` returned, append the result, repeat until the model emits a final answer.
6. Worker streams events back to the supervisor over a pipe.
7. Supervisor writes the audit log, returns the final reply, the worker exits.

One request = one worker = one `run_id` in the audit log. Workers do not talk to each other.

## What goes where — a mental cheat sheet

> "I want the agent to learn a new way of *doing things*." → write a **skill**.
>
> "I want the agent to be able to *perform a new action* on the world." → write a **tool** (and a card).
>
> "I want to give a *new persona* access to a curated set of skills." → write a **pack**.
>
> "I want to change *how* the orchestrator routes or spawns workers." → that's framework work, propose it.

## Glossary

- **Frontmatter** — the YAML block at the top of `SKILL.md` or a tool card. Always-in-context metadata.
- **Progressive disclosure** — the model sees frontmatter cheaply, loads the body when a skill activates, loads references on demand. Keeps token cost low.
- **Tool card** — the markdown doc describing a tool. Its body becomes the tool's `description` sent to the model.
- **Manifest** — `manifest.yaml` inside a skill folder. Declares which tools the skill needs and what permissions/classifications are involved.
- **Pack** — a YAML file in `packs/`. Lists the skills a persona gets.
- **Run** — one user request handled end-to-end by one worker. Has a unique `run_id`.
- **Classification** — a tag (`public`, `internal`, `confidential`, `restricted`) on tools and skills. Packs declare a ceiling; the framework refuses to bind tools above it.
