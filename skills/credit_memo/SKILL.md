---
name: credit_memo
description: >
  Use this skill when the user asks you to draft, prepare, or assemble a
  credit memo for a corporate borrower. The user typically supplies either a
  borrower name (which you fetch from the docstore) or an attached
  spreadsheet of financials. Produces a structured draft memo for human
  review. Do not assign a final risk rating — that is the human reviewer's
  decision.
version: 0.1.0
---

# Credit memo

## When this skill applies

The user wants a draft credit memo for a corporate borrower. Triggers:

- "Draft a credit memo for <Company X>"
- "Prepare the credit note on counterparty <name>"
- "I've attached the financials, draft the memo"

Do not use this skill for:
- KYC screening — that is `kyc_screening` (when available).
- Producing a final approval decision — this skill only drafts; humans approve.

## Workflow

1. Identify the borrower. The user provides either:
   - A company name → fetch the credit input via
     `docstore.fetch(query=<name>, doc_type="credit_input")`.
   - A spreadsheet path → call `xlsx.read(path=<path>)` to get the financials.
   - Both → use both as parallel inputs.

2. If `docstore.fetch` returns `error.code = "not_found"`, ask the user
   whether they want to proceed with just the attached spreadsheet, or
   provide a different identifier. Do not invent data.

3. From the fetched text, call `text.extract_lines(text=<body>)` to surface
   the quantitative and structured lines.

4. Assemble the draft memo with these sections, in this order:
   - **Borrower** — name, jurisdiction, sector.
   - **Facility** — amount, tenor, pricing, purpose.
   - **Financial highlights** — quote the relevant numeric lines verbatim
     (with line numbers from `text.extract_lines`).
   - **Risks** — quote the relevant lines verbatim.
   - **Recommendation** — leave blank, with the placeholder
     `_[to be filled by human reviewer]_`.

5. Before returning, check the draft length with `text.word_count`; if it
   exceeds 600 words, tighten the prose, never drop the numeric lines.

## Conventions

- Express monetary amounts in millions with currency code (e.g. `EUR 75m`).
- Round ratios to two decimals (`Net debt / EBITDA: 2.45x`).
- Quote financial lines verbatim from the source. If you paraphrase, append
  the original line in italics on the next line.
- Tag every fact with its source: `[docstore:<id>]` or `[xlsx:<sheet>:<row>]`.
- Use ISO-8601 dates.

## Edge cases

- **Conflicting figures** between the docstore document and the spreadsheet:
  show both, tag both, and flag the discrepancy under a "Data quality"
  callout at the top of the memo.
- **Stale data** (docstore doc older than 12 months): include a warning
  banner at the top.
- **Missing facility details**: leave the Facility section with explicit
  `_[missing]_` placeholders; do not invent values.

## References

- `references/memo-skeleton.md` — the exact section ordering and markdown
  template; load when assembling.
