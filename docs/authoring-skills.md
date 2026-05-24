# Authoring skills

A **skill** teaches the agent how to handle a class of tasks using tools that already exist. A skill has two artifacts:

1. **`SKILL.md`** — the playbook, written in the voice of a senior analyst briefing a junior.
2. **`manifest.yaml`** — declares which tools the skill needs and what classification it operates at.

A skill **never** ships its own tools. If you find yourself needing a capability that doesn't exist, you write a tool first (see `authoring-tools.md`), get it merged into the catalog, then write your skill against it.

## The golden rules

1. **No shell. No install. No code blocks the model is supposed to execute.** Every action is a tool call by name.
2. **Skills don't own tools.** They consume tools from `tools/<domain>/`. A skill folder contains only `SKILL.md`, `manifest.yaml`, and optional `references/` and `assets/`.
3. **Write for the model, not for developers.** SKILL.md is prompt context. The reader is the LLM.
4. **Workflow over knowledge dump.** A skill is "when X happens, do A then B; if Y, do C instead." Encyclopedic background goes in `references/`, loaded on demand.
5. **Keep `SKILL.md` under 500 lines.** If it grows beyond that, split into references.
6. **Every "run this" line is a bug.** Reject in review.

## File layout

```
skills/<skill_name>/
├── SKILL.md
├── manifest.yaml
├── references/        # optional, loaded on demand by the model
│   └── <topic>.md
└── assets/            # optional, static files (templates, examples)
    └── <file>
```

## `SKILL.md` structure

```markdown
---
name: <skill_name>
description: >
  Use this skill when <specific triggers>. Be precise — the model uses this
  string to decide whether to activate the skill at all. Include concrete
  nouns ("a credit memo", "an internal compliance brief") and verbs ("draft",
  "review", "extract from").
version: 0.1.0
---

# <Skill name>

## When this skill applies
Restate the triggers in fuller prose. The frontmatter `description` is the
one-line summary; this section is the model's first read after activation.

## Workflow
A numbered or bulleted procedure the model follows. Reference tools by name.

1. Fetch the source document with `docstore.fetch(doc_id=...)`.
2. If the source is an .xlsx, call `xlsx.read(path=...)`; for a .pdf, call `pdf.extract_text(path=...)`.
3. Summarize the financial highlights with `text.summarize(...)`.
4. Draft the memo using the template in `references/memo-template.md`.
5. Return the draft for human review.

## Conventions
Style, formatting, tone, units, naming conventions. These are the things a
senior analyst would tell a junior at the start of a project.

- Always express monetary amounts in millions with currency code (e.g. "EUR 12.4m").
- Round percentages to one decimal.
- Use the bank's standard rating scale (AAA → D).

## Edge cases
- If `docstore.fetch` returns `error.code = "not_found"`, ask the user for an alternative document reference rather than guessing.
- If the source covers multiple entities, ask the user which entity is the subject.

## References
- `references/memo-template.md` — the canonical memo skeleton; load when drafting.
- `references/rating-scale.md` — the bank's internal rating definitions; load if rating is required.
```

### Writing the `description` (frontmatter)

This is the **only** part of your skill that lives in context permanently. The router uses it to decide whether to activate the skill at all. Get it wrong and your skill never fires.

- **Lead with triggers**, not capabilities. *"Use this skill when the user asks to draft a credit memo for a corporate borrower"* beats *"This skill drafts credit memos."*
- **Name concrete artifacts** — file types, document names, output formats.
- **Mention adjacent skills it should NOT replace** if the description risks collision.

### Workflow vs Conventions vs Edge cases

These three sections do different jobs. Keep them separate.

- **Workflow** is the happy path: what tools, in what order, to produce the expected output.
- **Conventions** is the style guide: things the model would otherwise get plausibly but wrongly.
- **Edge cases** is the branch table: known failure modes and how to recover.

If you only write one, write **Workflow**. If your skill is non-trivial, you almost certainly need all three.

## `manifest.yaml` structure

```yaml
name: credit_memo
version: 0.1.0
owner: team-credit-ai

requires_tools:
  - docstore.fetch
  - xlsx.read
  - pdf.extract_text
  - text.summarize

classification: confidential       # ceiling at which this skill operates
data_sources: [internal_docs, market_data]

permissions:
  - fs.read
  - fs.write
```

Field meanings:

- **`requires_tools`**: every tool the skill ever calls. The framework validates each name exists in the registry and that its classification is ≤ the skill's. **No wildcards.** If your skill calls a tool conditionally, still list it.
- **`classification`**: the data sensitivity level this skill is allowed to handle. A pack inherits the max of its skills' classifications.
- **`owner`**: the team that maintains the skill and is paged when its evals fail.
- **`permissions`**: coarse-grained capability flags. Used for audit reporting, not runtime enforcement (tools enforce their own access).

## Progressive disclosure — three levels

| Level | What | When loaded | Token cost |
|---|---|---|---|
| 1. Frontmatter `description` | One-line summary | Always (in supervisor's catalog) | Low |
| 2. `SKILL.md` body | The full playbook | When the skill activates for this run | Medium |
| 3. `references/*.md` | Deep guidance, templates | On demand, when the model reads the path | Pay per use |

**Rule of thumb**: anything used >50% of the time goes in the body. Anything used <50% of the time goes in references, with a clear pointer from the body ("for the memo template, read `references/memo-template.md`").

## How to choose tools from the catalog

Before writing your `manifest.yaml`:

1. Open `docs/tool-catalog.md`.
2. For each step in your workflow, find the closest existing tool. Use **tags** (`[read]`, `[summarize]`, `[chart]`) to browse.
3. If you can't find one within ~80% of what you need:
   - Could you adjust your workflow to use what exists? Often yes.
   - If genuinely no, propose a new tool (see `authoring-tools.md`) **as a separate PR before your skill PR**.
4. **Never** write a private helper script in the skill folder. There is no `scripts/` directory inside a skill.

## Worked example

See `docs/example-kyc-screening.md` for an end-to-end skill walked through:
the `SKILL.md`, the `manifest.yaml`, the three tools it depends on (with their cards), and the pack that includes it.

## Checklist before opening a PR

- [ ] `SKILL.md` is under 500 lines.
- [ ] Frontmatter `description` leads with concrete triggers.
- [ ] **Workflow** references tools by exact name; no shell, no install, no code-to-execute.
- [ ] **Conventions** and **Edge cases** present if the skill is non-trivial.
- [ ] `manifest.yaml` lists every tool actually called.
- [ ] Every listed tool exists in the catalog and is at or below the skill's classification.
- [ ] At least one eval in `tests/evals/<skill_name>/` — golden input, expected tool-call trace.
- [ ] `python scripts/check_catalog.py` is green.
