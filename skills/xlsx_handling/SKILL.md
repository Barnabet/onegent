---
name: xlsx_handling
description: >
  Use this skill whenever the user gives you a path to a `.xlsx`, `.xlsm`,
  `.csv`, or `.tsv` file and wants anything done with it — inspect it, read
  rows, answer a question that needs computation over the data (sums,
  averages, group-bys, joins, filters, top-N), create a new workbook,
  edit cells, format cells, recalculate formulas, or convert between
  spreadsheet formats. Append this skill on top of whatever pack is running;
  it composes cleanly with others. Multi-sheet workbooks are first-class.
  Do not use this skill for `.pdf` (use `pdf_handling`), `.docx`, or `.pptx`.
version: 0.1.0
---

# Spreadsheet handling

## When this skill applies

The user mentions a spreadsheet file (path, attachment, or describes one) and
wants to read, query, transform, create, edit, format, recalculate, or
convert it. Typical triggers:

- "What's in `<path>.xlsx`?"
- "How much did region X spend last quarter?" (against a workbook/CSV)
- "Sum the `amount` column of `loans.csv`."
- "Join customers.csv with orders.xlsx and show top 10 spenders."
- "Build me a workbook with one sheet per region."
- "Set cell B11 to `=SUM(B2:B10)` then recalc."
- "Make the header row bold and format column C as currency."
- "Convert `report.xlsx` to CSV." or "Split every sheet into its own CSV."

## Workflow — pick the first call from this table

| User wants | First call |
|---|---|
| Quick overview ("what is this file?") | `xlsx.info(path=...)` |
| The raw rows (small file, sample, dump) | `xlsx.read(path=..., sheet=<optional>)` |
| Every sheet's rows at once | `xlsx.read(path=..., all_sheets=true)` |
| **Any answer that needs computation** (sum, avg, group-by, join, filter, top-N) | `xlsx.sql(inputs=[...], query="SELECT ...")` |
| Create a new workbook | `xlsx.write(output=..., sheets={...})` |
| Edit specific cells | `xlsx.edit_cells(path=..., output=..., cells=[{cell,value}, ...])` |
| Apply styling | `xlsx.format(path=..., output=..., range=..., ...)` |
| Materialise formula results | `xlsx.recalc(path=...)` |
| Convert / explode sheets | `xlsx.convert(path=..., output=..., explode_sheets=<bool>)` |

### The standard sequence for "tell me about this spreadsheet"

1. `xlsx.info(path=<path>)` to get the sheet inventory, shape, and header
   previews. Cheap, no row dump.
2. If the workbook has more than one sheet, pick the sheet(s) relevant to
   the question. If unclear, ask the user.
3. If the user wants computation, jump straight to `xlsx.sql` — do **not**
   read all rows first.
4. If the user wants a sample/preview, call `xlsx.read(path=..., sheet=...)`
   and show the first ~5–10 rows as a fenced table.
5. Summarise: shape per sheet, column names verbatim, and (if relevant) the
   answer to the user's question.

### When to use `xlsx.sql` (the rule)

**If the answer to the user's question involves any of {sum, average, count,
min, max, group, distinct, percentile, join, sort-and-pick, filter-and-count,
top-N, ratio, year-over-year}, use `xlsx.sql`. Do not pull rows with
`xlsx.read` and compute in your head — it is slower, easier to get wrong, and
wastes tokens.**

Typical pattern:

1. `xlsx.info(path=...)` to learn the sheet/column names.
2. Build a SQL query referencing those names. Quote identifiers with
   double-quotes when they contain spaces or punctuation
   (`SELECT "Net Revenue" FROM Revenue`).
3. Call `xlsx.sql(inputs=[...], query="...")`.
4. Report the returned `columns` + `rows` as a small table. If
   `truncated=true`, mention it.

For multi-sheet workbooks, every sheet loads as its own table. With a sheet
name like `Q1 Revenue`, the table becomes `Q1_Revenue` (non-identifier
characters → `_`); the `tables` field in the result shows the mapping. Use
`alias=` to disambiguate when joining workbooks that share sheet names.

### Multi-sheet workbooks

- Treat sheet selection as a first-class decision. Never silently pick the
  first sheet on a multi-sheet workbook for an ambiguous question; call
  `xlsx.info` and either pick the obviously-correct sheet or ask.
- For "everything across all sheets", `xlsx.sql` with no `sheet` filter loads
  every sheet as a table — use `UNION ALL` to combine.
- For "give me every sheet's rows", `xlsx.read(all_sheets=true)`.
- For "save each sheet as its own CSV", `xlsx.convert(..., explode_sheets=true)`.

### Creating a workbook from scratch

1. Build the rows in memory (often via the previous tool calls or via
   `xlsx.sql` against the source files).
2. Call `xlsx.write` — pass `sheets={...}` for multi-sheet output, or
   `headers`/`rows`/`sheet_name` for single-sheet.
3. If any cell is a formula (string starts with `=`), follow with
   `xlsx.recalc` so the values are materialised in the file.
4. If the user asked for styling (bold headers, currency, highlighted
   assumptions, column widths), follow with `xlsx.format`.

### Editing an existing workbook

1. `xlsx.edit_cells` writes the new cell values, preserving everything else.
2. If you wrote any formula, call `xlsx.recalc` next.
3. Optional: `xlsx.format` to tweak styling.
4. The original input is never modified — `output` is always a fresh path.

### Formula correctness checklist (mandatory for any workbook with formulas)

- Verify cell references are right (off-by-one, far-right columns, NaN
  denominators that would yield `#DIV/0!`).
- Always run `xlsx.recalc` after writing formulas. If `status="errors_found"`,
  inspect `error_summary`, fix the formulas with another `xlsx.edit_cells`
  round, and recalc again. Deliver only when `total_errors == 0`.
- Prefer formulas over hardcoded computed values. If the user changes an
  assumption, the workbook should recompute.

## Conventions

- **Sheet selection is explicit.** On any multi-sheet workbook, decide which
  sheet you mean and pass `sheet=...`. Don't guess.
- **Identifier quoting in SQL.** Column or sheet names with spaces or
  punctuation must be quoted: `SELECT "Net Revenue" FROM "Q1 Revenue"`.
- **Numbers in output**: thousand separators and ≤2 decimals unless the
  values are clearly integer ids. For currency, use `'$#,##0;($#,##0);-'`.
  For percentages, `'0.0%'`. For multiples, `'0.0x'`.
- **Column names verbatim.** Do not normalise casing or whitespace when
  echoing column names to the user.
- **Output paths.** Never overwrite the input. Default to the same directory
  as the input with a suffix like `-edited.xlsx`, `-recalc.xlsx`,
  `-styled.xlsx`. If unsure, propose one and proceed; pass `overwrite=true`
  only if the user explicitly asked.
- **Big files.** If a single sheet has >5,000 rows or >50 columns, prefer
  `xlsx.sql` for any answer; only `xlsx.read` when the user explicitly wants
  raw rows, and warn them about the size first.
- **Financial-model colour code.** When the user is building a financial
  model and hasn't given a style preference, follow the standard: blue
  text (`0000FF`) for hardcoded inputs, black for formulas, green
  (`008000`) for cross-sheet links, red (`FF0000`) for external-file links,
  yellow fill (`FFFF00`) for key assumptions.

## Edge cases

- **`file_not_found`**: ask the user for a corrected path; do not guess.
- **`unsupported_format`**: the file is not tabular. If it's a `.pdf`,
  point at `pdf_handling`; for `.docx`/`.pptx`, tell the user there is no
  skill yet.
- **`sheet_not_found`**: re-run `xlsx.info` to get the true sheet names and
  re-issue with a valid one.
- **`forbidden_statement` / `sql_error` on `xlsx.sql`**: rewrite the query.
  `xlsx.sql` is read-only — only `SELECT`, `WITH`, or `VALUES`. No
  semicolons. Use double-quoted identifiers for odd column/sheet names.
- **`output_exists`**: pick a different filename or, if the user explicitly
  asked to replace, retry with `overwrite=true`.
- **`dependency_missing` on `xlsx.recalc`**: LibreOffice (`soffice`) is not
  installed. Tell the user; suggest skipping recalc (formula strings will
  remain unevaluated) or installing LibreOffice. Do not retry.
- **Mixed-type columns**: a column containing both `"$1,234"` strings and
  numbers will surprise SQL aggregations. Cast explicitly:
  `SUM(CAST(REPLACE(REPLACE(amount,'$',''),',','') AS REAL))`. Mention the
  cast in your reply.
- **CSV not UTF-8** (`decode_error`): ask the user for the source encoding
  or to re-save as UTF-8.

## References

- The upstream Anthropic `xlsx` skill (in `anthropic-skills/skills/xlsx/`)
  documents the underlying libraries (pandas, openpyxl, LibreOffice) and the
  formula / formatting conventions. This skill exposes the same capabilities
  as tool calls; do not shell out or write Python yourself.
