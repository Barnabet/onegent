# Worked example: `kyc_screening`

A complete, end-to-end skill walkthrough. Read top to bottom. This is what good looks like in v0.1 of the library.

The scenario: a KYC reviewer needs to screen a new corporate counterparty. They paste the counterparty name; the agent fetches the latest available KYC dossier, summarises the entity, runs an adverse-media check, and produces a structured screening note.

By the end of this doc you will have seen:

1. The pack (`packs/kyc_reviewer.yaml`).
2. The skill (`skills/kyc_screening/`) — `SKILL.md` + `manifest.yaml`.
3. The three tools the skill uses, each with a full card:
   - `docstore.fetch` — already exists in the catalog (reused).
   - `text.summarize` — already exists (reused).
   - `web.adverse_media_search` — new, written for this skill but designed to be reusable by future ones.

---

## 1. The pack

`packs/kyc_reviewer.yaml`

```yaml
name: kyc_reviewer
version: 0.1.0
owner: team-financial-crime-ai

description: >
  Bundle for KYC analysts screening corporate counterparties:
  fetching dossiers, summarising entities, running adverse-media checks.

skills:
  - kyc_screening

classification: confidential
allowed_data_sources:
  - internal_docs
  - public_web

model: claude-sonnet-4-6

limits:
  max_tool_calls_per_run: 20
  max_tokens_per_run: 120000
  timeout_seconds: 180

risk_review:
  reviewed_by: risk-ai-committee
  reviewed_at: 2026-05-15
  ticket: RISK-1284
```

Notes:

- The pack lists **one skill**. That's fine — packs grow as the persona's surface grows. Starting small keeps the classification ceiling tight.
- `classification: confidential` is required because internal KYC dossiers are confidential.
- `allowed_data_sources` includes `public_web` because adverse-media search hits the open internet.

---

## 2. The skill

### `skills/kyc_screening/manifest.yaml`

```yaml
name: kyc_screening
version: 0.1.0
owner: team-financial-crime-ai

requires_tools:
  - docstore.fetch
  - text.summarize
  - web.adverse_media_search

classification: confidential
data_sources:
  - internal_docs
  - public_web

permissions:
  - fs.read
```

### `skills/kyc_screening/SKILL.md`

```markdown
---
name: kyc_screening
description: >
  Use this skill when the user asks to screen, review, or produce a KYC note
  for a corporate counterparty — typically by giving you a company name, a
  legal entity identifier (LEI), or an internal counterparty id. Produces a
  structured screening note covering entity summary and adverse media.
version: 0.1.0
---

# KYC screening

## When this skill applies

The user wants a KYC screening of a corporate counterparty. Triggers include:

- "Screen <Company X> for me"
- "Run KYC on counterparty 12345"
- "Give me a screening note on <LEI>"

Do not use this skill for individuals (PEP screening is a separate skill).
Do not use it to draft full enhanced due diligence reports — those go through
a different workflow.

## Workflow

1. Identify the counterparty. The user will give one of:
   - A company name (string).
   - An LEI (20-character alphanumeric).
   - An internal counterparty id (numeric).

   If ambiguous, ask the user to confirm before fetching.

2. Fetch the latest KYC dossier:

   `docstore.fetch(query=<identifier>, doc_type="kyc_dossier", latest=true)`

   If the result is `error.code = "not_found"`, ask the user whether they want
   to proceed with public-data-only screening; do not invent a dossier.

3. Summarise the entity from the dossier using:

   `text.summarize(text=<dossier_body>, style="kyc_entity", max_tokens=400)`

   The `kyc_entity` style focuses on: registered name, jurisdiction, ultimate
   beneficial owners, sector, year founded, group structure.

4. Run an adverse-media check on the entity's registered name:

   `web.adverse_media_search(entity=<registered_name>, lookback_months=24)`

   The tool returns a ranked list of hits with source, date, severity, and
   one-line summary.

5. Assemble the screening note using the structure in
   `references/note-template.md`. Cite every adverse-media hit with its URL.

6. Return the note. Do not assign a risk rating — that is the human reviewer's
   decision. Flag clearly any section where data was missing.

## Conventions

- Always use the registered legal name (not trade names) for the adverse-media
  search; trade-name searches produce false positives.
- Express dates as ISO-8601 (YYYY-MM-DD).
- Quote adverse-media headlines verbatim; do not paraphrase.
- Mark every section produced from public-web data with a `[public-web]` tag
  so the human reviewer can weight it appropriately.

## Edge cases

- **Dossier older than 18 months**: include a warning banner at the top of the
  note ("Dossier last refreshed YYYY-MM-DD; consider requesting a refresh").
- **Adverse-media tool returns >50 hits**: do not list all of them. Return the
  top 10 by `severity` and mention the total count.
- **Counterparty operates in a sanctions-sensitive jurisdiction**: do not
  produce the note; respond with "Sanctions screening required first" and ask
  the user to escalate to the sanctions desk.

## References

- `references/note-template.md` — the canonical screening note skeleton.
- `references/sensitive-jurisdictions.md` — the bank's current list of
  jurisdictions requiring sanctions screening first; load when checking step 4.
```

Notes on what makes this skill correct:

- The `description` leads with **triggers**, names concrete inputs (company name, LEI, id), and names the output (a screening note). It also negatively scopes ("do not use this skill for individuals") so the router doesn't fire it for PEP requests.
- The workflow names tools **by exact registered name**. No shell, no `python ...`, no library imports.
- **Conventions** captures the things a senior KYC analyst would say to a junior — which are not "common sense" for the model.
- **Edge cases** is the branch table that protects the firm from the obvious failure modes.
- `references/` holds the template and the sensitive-jurisdictions list. They are loaded only when needed.

---

## 3. The tools

The skill declares three tools. Two are reused from the catalog; one is new.

### 3a. `docstore.fetch` — reused

This tool already exists. The skill just declares it in `requires_tools`. No new code, no new card. This is the **reuse principle** at work.

The author opened `docs/tool-catalog.md`, searched for "fetch", found `docstore.fetch`, read its card, confirmed it accepts `query` strings and `doc_type` filters, and wrote the workflow against it. Total skill-side cost: zero lines of code.

### 3b. `text.summarize` — reused

Already exists. Note how the skill uses the `style="kyc_entity"` parameter — the `text.summarize` card documents a small enum of summary styles. When KYC needed a new style, the right move was a **minor version bump of `text.summarize`** (adding `kyc_entity` to the enum and documenting it in the card), **not** a new tool `kyc.summarize_entity`. That kept the catalog small and the skill simple.

### 3c. `web.adverse_media_search` — new tool, written for this skill

This capability didn't exist. Before writing the skill, the author shipped this tool **in a separate PR**, with a card designed for reuse by future skills (sanctions screening, ongoing monitoring, M&A target diligence).

**`tools/web/registry.py`** (excerpt)

```python
from pydantic import BaseModel, Field
from typing import Optional
from runtime.tool_registry import tool, ToolCtx, ToolResult

class AdverseMediaParams(BaseModel):
    entity: str = Field(..., description="Registered legal name of the entity")
    lookback_months: int = Field(24, ge=1, le=120)
    languages: Optional[list[str]] = Field(None, description="ISO 639-1 codes; default: en,fr")
    max_results: int = Field(25, ge=1, le=100)

@tool(
    name="web.adverse_media_search",
    card="cards/adverse_media_search.md",
    schema=AdverseMediaParams,
    classification="internal",
    owner="team-financial-crime-ai",
    tags=["web", "search", "adverse-media", "due-diligence"],
)
def adverse_media_search(params: AdverseMediaParams, ctx: ToolCtx) -> ToolResult:
    # implementation calls the bank's vetted web-search provider
    ...
```

**`tools/web/cards/adverse_media_search.md`** — the full card

```markdown
---
tool: web.adverse_media_search
version: 1
owner: team-financial-crime-ai
classification: [internal]
tags: [web, search, adverse-media, due-diligence]
---

# web.adverse_media_search

## Purpose
Search the open web for negative news about a named entity, ranked by
relevance and severity, restricted to vetted news sources.

## When to use
- KYC screening of a corporate counterparty.
- Periodic monitoring of an existing counterparty for new adverse media.
- M&A target due diligence — reputational risk pass.

## When NOT to use
- For sanctions list checks, use `compliance.sanctions_check` — it hits
  official lists, not news.
- For PEP screening of individuals, use `compliance.pep_screen` — different
  data sources and severity model.
- For general open-web search, use `web.search` — this tool is restricted to
  vetted news sources and applies an adverse-media classifier.

## Parameters
| name | type | required | description |
|---|---|---|---|
| entity | string | yes | Registered legal name of the entity. Use the legal name, not trade names — trade names produce false positives. |
| lookback_months | int | no | How far back to search; default 24, max 120. |
| languages | list[string] | no | ISO 639-1 codes, e.g. ["en","fr"]; default ["en","fr"]. |
| max_results | int | no | Cap on returned hits, default 25, max 100. |

## Returns
On success:
```
{
  ok: true,
  data: {
    entity: "<echoed>",
    total_hits: 42,
    returned: 25,
    hits: [
      {
        url: "...",
        source: "Reuters",
        published: "2025-08-12",
        severity: "high",            # high | medium | low
        category: "fraud-allegation",
        headline: "...",
        summary: "..."
      },
      ...
    ]
  },
  citations: [<one per hit>]
}
```

## Errors
- `entity_too_generic` — name too short or matches >1000 entities (e.g. "ABC").
- `provider_unavailable` — upstream news provider down; `retriable: true`.
- `language_unsupported` — one of the requested languages is not supported.

## Examples
### Default screening over 2 years, EN+FR
Call: `web.adverse_media_search(entity="Globex Corporation SA")`
Returns: `{ok: true, data: {entity: "Globex Corporation SA", total_hits: 18, returned: 18, hits: [...]}}`

### Wider lookback for periodic monitoring
Call: `web.adverse_media_search(entity="Globex Corporation SA", lookback_months=60, max_results=50)`

### Italian-language coverage
Call: `web.adverse_media_search(entity="Acme Italia SpA", languages=["it","en"])`

## See also
- `compliance.sanctions_check` — official sanctions lists, not news.
- `compliance.pep_screen` — politically-exposed-persons screening for individuals.
- `web.search` — unrestricted web search, no adverse-media classifier.
```

Notes on what makes this tool — and especially its card — correct:

- **Designed for reuse from day one.** The `tags` list and the cross-links in **When NOT to use** anticipate three other skills that will eventually use it (sanctions screening, periodic monitoring, M&A diligence). It is *not* called `kyc.adverse_media`.
- The **When NOT to use** section is the longest of the card. This is the right ratio. It links to two adjacent tools (`compliance.sanctions_check`, `compliance.pep_screen`) and one general-purpose tool (`web.search`). The model now knows when to pick it and when not to.
- **Parameter descriptions explain semantics** — "use the legal name, not trade names" is the kind of guidance only the card can carry. The pydantic schema can't.
- **Errors are enumerated with `retriable` semantics** baked into how the model thinks: `provider_unavailable` is retriable, `entity_too_generic` is not.
- The classification is `internal` (the search results themselves are not bank-confidential), but the **skill** is `confidential` because it combines those results with internal dossier data. This is exactly how the layered classification model is supposed to work.

---

## 4. What this example demonstrates

| Principle | How this example shows it |
|---|---|
| Tools are shared, not skill-owned | `docstore.fetch` and `text.summarize` are reused unchanged; the one new tool is named `web.adverse_media_search`, not `kyc.adverse_media`. |
| No shell, no install | Every action in `SKILL.md` is a tool call by name. There is no `scripts/` folder anywhere. |
| Tool cards drive correct selection | The new tool's card devotes its longest section to **When NOT to use** with three cross-links. |
| Progressive disclosure | The skill body is short; the note template and sensitive-jurisdictions list live in `references/`, loaded on demand. |
| Layered classification | Tool `internal` + skill `confidential` + pack `confidential`. The framework verifies the chain. |
| Reuse-first authoring | Adding `style="kyc_entity"` to `text.summarize` (minor bump) beat creating `kyc.summarize_entity`. |

Use this document as the reference when reviewing other people's first skill+tool PRs.
