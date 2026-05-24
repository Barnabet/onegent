---
name: skill_creator
description: >
  Use this skill when the user wants to create a new tool, skill, or pack
  for this library — typically phrases like "create a new skill", "add a
  tool for X", "scaffold a pack for Y", "I want to extend the library".
  This skill walks the user through the authoring process, consults the
  live authoring docs and catalog, enforces dedup checks, and scaffolds the
  files. Do not use this skill to *write the implementation* of a new tool
  — it only produces the scaffold; the user fills in the Python.
version: 0.1.0
---

# Skill creator

## When this skill applies

The user wants to extend the library by adding a new tool, skill, or pack.
They are not asking you to do work *with* an existing skill — they want to
*author* a new artifact.

If you are unsure whether the user wants to author a new artifact or use an
existing one, ask: "Do you want to create a new skill/tool/pack, or use an
existing one to do something?"

## Workflow

### Step 1 — Identify the artifact

Ask the user, in one short message, which of the three they want to create:

- a new **tool** (a Python capability the agent can call),
- a new **skill** (a playbook composing existing tools),
- a new **pack** (a persona bundling existing skills).

Then load the relevant authoring doc verbatim via `repo.read_doc`:

- tool   → `repo.read_doc(path="authoring-tools.md")`
- skill  → `repo.read_doc(path="authoring-skills.md")`
- pack   → `repo.read_doc(path="authoring-packs.md")`

Treat that doc as the source of truth. If anything in this skill disagrees
with the doc, the doc wins.

### Step 2 — Inventory

Call `repo.read_catalog()` once and keep the result in mind. You will use it
in steps 3 and 4 to check that referenced tools/skills exist.

### Step 3a — If creating a tool

1. Ask the user for the proposed `<domain>.<verb>` name and one-sentence
   purpose.

2. Dedup check (mandatory): call
   `repo.search_catalog(query="<verb or purpose-key-words>")`. Show the user
   the top hits. If any hit looks similar, ask the user to either:
   - extend the existing tool (recommended), or
   - explicitly justify why a new tool is needed (and you record that
     justification in your reply so it appears in the audit log).

3. Confirm the owner team name with the user.

4. Walk through filling out the tool card sections in conversation:
   Purpose, When to use, When NOT to use (with cross-links to neighbours),
   Parameters, Returns, Errors, Examples. Use the worked example via
   `repo.read_doc(path="example-kyc-screening.md")` as the reference for
   what good looks like.

5. Call `repo.scaffold_tool(name=<name>, owner=<owner>)`.

6. Surface the `next_steps` list from the tool result verbatim and stop.
   Tell the user you cannot implement the Python for them — that is a
   human/engineering step.

### Step 3b — If creating a skill

1. Ask for the proposed skill name (lowercase + underscores), the owner
   team, and the persona's intended classification.

2. Ask the user to describe the workflow in natural language, step by step.

3. For each workflow step, call `repo.search_catalog(query=<step-keywords>)`
   to find existing tools. Propose the best candidate to the user; if none
   exists, **stop and tell them to create the tool first** using
   skill_creator's tool branch.

4. Once every step maps to an existing tool, present the final
   `requires_tools` list to the user for confirmation.

5. Call `repo.scaffold_skill(name=<name>, owner=<owner>,
   requires_tools=<list>, classification=<level>,
   data_sources=<list-or-omit>)`.

6. Surface the result's `next_steps`. Remind the user to write the
   `## Workflow`, `## Conventions`, and `## Edge cases` sections in the
   generated SKILL.md.

### Step 3c — If creating a pack

1. Ask for pack name, owner, persona description, and the candidate skill
   list.

2. Validate every named skill exists by consulting the catalog you fetched
   in step 2.

3. Ask for the pack's classification ceiling. If `confidential` or above,
   remind the user that a `risk_review` block will need to be added by hand
   before the pack can load.

4. Call `repo.scaffold_pack(name=<name>, owner=<owner>,
   description=<one-paragraph>, skills=<list>, classification=<level>,
   model=<id-or-default>)`.

5. Surface the result's `next_steps`.

## Conventions

- Always consult the authoring doc via `repo.read_doc` at the start. Do not
  paraphrase the doc from memory.
- Never invent a tool, skill, or pack that already exists. The dedup check
  in step 3a is mandatory before any `repo.scaffold_tool` call.
- When you propose a name to the user, suggest two or three alternatives so
  they can pick. Naming is a one-shot decision; force a moment of thought.
- If the user pushes back on the dedup result, do not silently scaffold —
  ask them to confirm in one explicit reply.

## Edge cases

- If `repo.search_catalog` returns `error.code = "empty_query"`, ask the
  user for a more specific name or purpose; do not retry with the same
  query.
- If `repo.scaffold_*` returns `error.code = "already_exists"`, tell the
  user the artifact already exists, suggest they look at the catalog, and
  stop. Do not propose a renamed variant on your own.
- If the user wants to create multiple artifacts in one session, complete
  one fully, then ask whether they want to start the next.

## References

- The authoring docs themselves are the canonical reference — load them at
  runtime via `repo.read_doc`. There are no skill-local references because
  the source of truth lives in `docs/`.
