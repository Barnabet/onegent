# Authoring packs

A **pack** is a curated bundle of skills given to a sub-agent. Packs map to **personas** — "credit analyst", "KYC reviewer", "pitchbook drafter" — not to individual users.

Packs are the unit of governance. They are PR-reviewed, risk-signed, and pinned to a classification ceiling.

## The golden rules

1. **Packs declare skills, not tools.** Tools come along transitively via each skill's manifest.
2. **One pack = one persona = one risk profile.** Don't bundle "credit + KYC + treasury" into one mega-pack; that defeats least-privilege.
3. **Classification ceiling is enforced.** A pack with `classification: internal` cannot include a skill — or transitively a tool — at `confidential` or above. The framework refuses to bind.
4. **Pack changes go through risk review.** Code review is necessary; not sufficient.

## File layout

Packs live flat in `packs/`:

```
packs/
├── credit_analyst.yaml
├── kyc_reviewer.yaml
└── pitchbook_drafter.yaml
```

## Pack structure

```yaml
name: credit_analyst
version: 0.1.0
owner: team-credit-ai

description: >
  Bundle for credit analysts drafting and reviewing corporate credit memos.
  Includes document fetch, spreadsheet analysis, and memo drafting skills.

skills:
  - credit_memo
  - xlsx_analysis
  - financial_summary

classification: confidential       # ceiling — see below
allowed_data_sources:
  - internal_docs
  - market_data

# Model selection — overrides the default in runtime config.
# Keep packs on a specific model version for reproducibility of evals.
model: claude-sonnet-4-6

# Per-pack guardrails
limits:
  max_tool_calls_per_run: 40
  max_tokens_per_run: 200000
  timeout_seconds: 300

# Audit/governance metadata
risk_review:
  reviewed_by: risk-ai-committee
  reviewed_at: 2026-05-15
  ticket: RISK-1284
```

## Field meanings

- **`skills`** — the skills loaded into the sub-agent. The union of their `requires_tools` becomes the bound tool set.
- **`classification`** — the maximum data sensitivity this pack can handle. The framework computes the actual transitive classification (max over skills, max over tools) at load time. If the actual exceeds the declared ceiling, **the pack fails to load** with a clear error.
- **`allowed_data_sources`** — a coarse allow-list used by tools that read external systems. Tools check `ctx.allowed_data_sources` before fetching.
- **`model`** — pinned model id. Evals are tied to this; bumping the model is a pack version bump and triggers eval re-run.
- **`limits`** — runtime guardrails enforced by the supervisor. Exceeding them aborts the run with a structured error.
- **`risk_review`** — required for any pack at `confidential` or above. CI rejects PRs that bump classification without updating this block.

## How a pack composes tools

You don't list tools in a pack. You list skills, and the framework computes:

```
bound_tools(pack) = ⋃ requires_tools(skill) for skill in pack.skills
```

This is intentional. The skill ↔ tool relationship is curated by the skill author with domain expertise. The pack author chooses skills based on persona need. Mixing both concerns at the pack level invites drift.

## Choosing skills for a pack

1. Start from the persona's actual job. List 3–7 recurring tasks they do.
2. For each task, find a skill in `docs/skill-catalog.md` that fits.
3. If a skill is missing, write it (see `authoring-skills.md`) **as a separate PR before the pack**.
4. Avoid the temptation to add skills "just in case". Every added skill widens the tool surface and the classification ceiling.

## Versioning

- Adding a skill → minor bump, risk review **if classification ceiling rises**.
- Removing a skill → minor bump, no risk review needed.
- Changing `classification`, `allowed_data_sources`, `limits`, or `model` → minor bump, **risk review required**.
- The same `risk_review.ticket` can cover multiple related pack changes if they ship together.

## Testing

Packs themselves don't have unit tests, but each pack must have at least one **integration eval** in `tests/evals/packs/<pack>/`:

- A realistic user prompt.
- The expected sequence of skill activations.
- The expected tool-call types (not exact arguments).
- An acceptance check on the final reply.

The eval runs in CI against the configured model. A failing pack eval blocks PR merge.

## Checklist before opening a PR

- [ ] Pack covers one coherent persona, not a hybrid.
- [ ] Every listed skill exists and is at or below the declared `classification`.
- [ ] `classification` declared explicitly, even if it matches the default.
- [ ] `limits` set to sensible values for the persona's typical workload.
- [ ] If `classification` is `confidential` or above, `risk_review` block filled.
- [ ] At least one eval in `tests/evals/packs/<pack>/`.
- [ ] `python scripts/check_catalog.py` is green.
