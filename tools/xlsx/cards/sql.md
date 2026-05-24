---
tool: xlsx.sql
version: 1
owner: team-doc-ai
classification: [internal]
tags: [spreadsheet, read, query, sql]
---

# xlsx.sql

## Purpose
Run a read-only SQL query over one or more spreadsheet files. Each input is
loaded into an in-memory SQLite database; every `.xlsx` sheet becomes its own
table. Use this whenever the user wants computation (sum, average, group-by,
join, filter, top-N, distinct) — never reimplement that in your head.

## When to use
- The user asks a question that requires aggregation, filtering, joining,
  sorting, or grouping over tabular data — even on a single sheet.
- The data is large enough that dumping rows via `xlsx.read` and computing in
  your head would be slow, wasteful, or unreliable.
- You need to join two files (e.g. a CSV against a sheet from a workbook).

## When NOT to use
- To dump the raw rows for a few-line preview — `xlsx.read` is simpler.
- To inspect schema / sheet names — use `xlsx.info` first, then craft the SQL.
- To *modify* a workbook — this tool is read-only. Use `xlsx.write` or
  `xlsx.edit_cells`.
- To read a PDF table — use `pdf.extract_tables`.

## Parameters
| name | type | required | description |
|---|---|---|---|
| inputs | list | yes | Each entry is either a path string or `{path, alias?, sheet?}`. `.xlsx` files load every sheet as a separate table; pass `sheet=...` to restrict, or `alias=...` to rename the table. |
| query | string | yes | A single read-only SQL statement (`SELECT`, `WITH`, or `VALUES`). SQLite dialect. No semicolons, no DDL/DML. |
| max_rows | int | no | Cap on returned rows (default 1000). |

### Table naming rules
- A CSV/TSV named `loans.csv` becomes table `loans`. Pass `alias` to rename.
- A workbook `report.xlsx` with sheets `Revenue`, `Costs` becomes tables
  `Revenue`, `Costs`. Pass `sheet="Revenue"` to load just one. With multiple
  files that share sheet names, pass `alias` to disambiguate (e.g.
  `alias="q1"` → tables become `q1_Revenue`, `q1_Costs`).
- Non-identifier characters in sheet names are replaced with `_`; the original
  name is returned in `data.tables`.
- The first row of each sheet/file is used as column names (sanitised the
  same way). Quote identifiers with double quotes if they contain odd
  characters: `SELECT "Net Revenue" FROM Revenue`.

### Type handling
- Values are inserted as their native Python types (text / number / null).
  Use `CAST("col" AS REAL)` if a column read as text needs arithmetic.

## Returns
```
{ok: true, data: {
  columns: ["col_a", "col_b", ...],
  rows: [[...], ...],
  row_count: <int>,
  truncated: <bool>,
  tables: {"<sqlite-table>": {"path": "...", "sheet": "..."}, ...}
}}
```

## Errors
- `file_not_found` — one of the input paths does not exist.
- `unsupported_format` — an input extension is not tabular.
- `sheet_not_found` — `sheet` filter does not match any sheet in the workbook.
- `invalid_input` — empty query, multiple statements, or no inputs.
- `forbidden_statement` — query is not `SELECT`/`WITH`/`VALUES`, or mentions a
  write keyword.
- `sql_error` — SQLite rejected the query (syntax error, unknown table, etc.).
- `dependency_missing` — openpyxl is not installed and an xlsx input was given.

## Examples
### Sum a column on a single CSV
Call:
```
xlsx.sql(
  inputs=["/data/loans.csv"],
  query="SELECT SUM(amount) AS total FROM loans"
)
```

### Aggregate across one sheet of a workbook
Call:
```
xlsx.sql(
  inputs=[{"path": "/data/report.xlsx", "sheet": "Revenue", "alias": "rev"}],
  query="SELECT region, SUM(net) AS net FROM rev GROUP BY region ORDER BY net DESC"
)
```

### Join two files
Call:
```
xlsx.sql(
  inputs=[
    {"path": "/data/customers.csv"},
    {"path": "/data/orders.xlsx", "sheet": "2024"}
  ],
  query="SELECT c.name, SUM(o.amount) AS spend FROM customers c JOIN \"2024\" o ON o.customer_id = c.id GROUP BY c.name"
)
```

### Join every sheet of a multi-sheet workbook
Call:
```
xlsx.sql(
  inputs=[{"path": "/data/quarterly.xlsx", "alias": "q"}],
  query="SELECT 'Q1' AS quarter, SUM(amount) FROM q_Q1 UNION ALL SELECT 'Q2', SUM(amount) FROM q_Q2"
)
```

## See also
- `xlsx.info` — discover sheet and column names before writing SQL.
- `xlsx.read` — when you need raw rows, not a computed answer.
