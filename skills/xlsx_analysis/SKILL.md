---
name: xlsx_analysis
description: >
  Use this skill when the user gives you a path to a spreadsheet
  (.xlsx/.xlsm/.csv/.tsv) and asks you to inspect, analyse, or summarise its
  contents. Produces a short structured rundown: shape, columns, notable
  numeric ranges, and a small set of representative rows. Do not use this
  skill if the user wants the spreadsheet *modified* — that's a future skill.
version: 0.1.0
---

# Spreadsheet analysis

## When this skill applies

The user provides a path to a spreadsheet file and asks you to read it, look
at it, summarise it, or check what's in it. They are not asking for the file
to be edited or for new charts to be generated.

## Workflow

1. Confirm the path looks like a spreadsheet (extension `.xlsx`, `.xlsm`,
   `.csv`, or `.tsv`). If not, tell the user and stop.
2. Call `xlsx.read(path=<path>)`. If the user named a specific sheet, pass
   `sheet=<name>`.
3. If the tool returns `error.code = "file_not_found"`, ask the user for a
   corrected path; do not guess.
4. From the returned `headers` and `rows`, build a short structured rundown:
   - Shape: `<row_count>` rows × `<n>` columns.
   - Columns: list `headers` verbatim.
   - For up to 3 numeric-looking columns, give min / max / mean (compute
     from `rows` directly, do not call another tool for this).
   - Show the first 3 rows as a fenced table.
5. If the file is large (>500 rows or >20 columns), say so explicitly and
   suggest the user narrow the request next time.

## Conventions

- Render numeric columns with thousand separators and 2-decimal precision
  unless the values are clearly integer ids.
- Quote column names verbatim — do not normalise casing or whitespace.
- Keep the final reply under 400 words. Use `text.word_count` on your draft
  if you are unsure.

## Edge cases

- If `headers` is null (the user passed `has_header=false`), describe the
  shape only and ask whether the first row should be treated as headers.
- If a column contains a mix of types, say so rather than computing
  statistics that don't make sense.
