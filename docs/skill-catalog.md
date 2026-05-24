# Skill catalog

Generated from skills/*/SKILL.md frontmatter. Do not edit by hand.
Re-render with `python scripts/check_catalog.py --write`.

**6 skills.**

## `credit_memo` &nbsp; <sub>v0.1.0</sub>

Use this skill when the user asks you to draft, prepare, or assemble a credit memo for a corporate borrower. The user typically supplies either a borrower name (which you fetch from the docstore) or an attached spreadsheet of financials. Produces a structured draft memo for human review. Do not assign a final risk rating — that is the human reviewer's decision.

## `hello` &nbsp; <sub>v0.1.0</sub>

Use this skill when the user asks for a connectivity / smoke-test of the agent platform — typically phrases like "say hi", "ping", "smoke test", "are you alive". The skill calls a no-op echo tool to prove the tool plumbing works end-to-end, then reports success.

## `pdf_handling` &nbsp; <sub>v0.1.0</sub>

Use this skill whenever the user gives you a `.pdf` path or asks to do anything with a PDF — read it, extract text or tables, look at a page, merge / split / rotate, encrypt or decrypt, fill a form, OCR a scan, or **author a brand-new PDF report / summary / one-pager from structured data** (use `pdf.create`). Append this skill on top of whatever pack is running; it composes cleanly with other skills. Do not use this skill for `.docx`, `.pptx`, or `.xlsx` files — there are (or will be) dedicated skills for those.

## `router` &nbsp; <sub>v0.4.0</sub>

Use this skill on every router turn. You are the user-facing orchestrator. The system prompt already lists every delegatable pack and every composable skill — you do NOT need a tool call to discover them. You may answer trivial questions yourself, and you may use the read-only file-inspection tools (pdf.*, xlsx.read) for small information-gathering on attached files. For any real work — analysis, generation, writing, transformation — you delegate via orchestrator.delegate and forward only the files the sub-agent needs.

## `skill_creator` &nbsp; <sub>v0.1.0</sub>

Use this skill when the user wants to create a new tool, skill, or pack for this library — typically phrases like "create a new skill", "add a tool for X", "scaffold a pack for Y", "I want to extend the library". This skill walks the user through the authoring process, consults the live authoring docs and catalog, enforces dedup checks, and scaffolds the files. Do not use this skill to *write the implementation* of a new tool — it only produces the scaffold; the user fills in the Python.

## `xlsx_handling` &nbsp; <sub>v0.1.0</sub>

Use this skill whenever the user gives you a path to a `.xlsx`, `.xlsm`, `.csv`, or `.tsv` file and wants anything done with it — inspect it, read rows, answer a question that needs computation over the data (sums, averages, group-bys, joins, filters, top-N), create a new workbook, edit cells, format cells, recalculate formulas, or convert between spreadsheet formats. Append this skill on top of whatever pack is running; it composes cleanly with others. Multi-sheet workbooks are first-class. Do not use this skill for `.pdf` (use `pdf_handling`), `.docx`, or `.pptx`.
