---
tool: pdf.extract_tables
version: 1
owner: team-doc-ai
classification: [internal]
tags: [pdf, read, tabular]
---

# pdf.extract_tables

## Purpose
Detect tables in a PDF and return their cell contents as 2-D arrays. Uses
`pdfplumber`'s line-based detection.

## When to use
- The user asks for the rows of a table in a PDF (e.g. a financial table, a
  rate sheet, a roster).
- A skill needs structured tabular data that exists *inside* a PDF rather
  than its own spreadsheet.

## When NOT to use
- For prose — use `pdf.extract_text`.
- For data that is rendered as an image (scanned tables) — use `pdf.ocr` and
  then parse the resulting text manually. Table detection on a scan returns
  nothing.
- If the source is a real `.xlsx` or `.csv`, never round-trip via PDF; use
  `xlsx.read` directly.

## Parameters
| name | type | required | description |
|---|---|---|---|
| path | string | yes | Path to a `.pdf` file. |
| pages | string | no | 1-based page spec; omit to scan the document's first `max_pages` pages. |
| max_pages | int | no | Cap on the number of pages scanned for tables (default 5). Applied after the `pages` spec. When the cap drops pages, the payload includes `truncated: true` and `skipped_pages: [...]`. |

## Returns
On success:
```
{
  ok: true,
  data: {
    table_count: <int>,
    tables: [
      {page: <1-based>, index: <1-based within page>, row_count, col_count, rows: [[cell, ...], ...]},
      ...
    ],
    // present only when truncated:
    requested_page_count: <int>,
    returned_page_count: <int>,
    skipped_pages: [<1-based>, ...],
    truncated: true,
    truncation_note: "Returned N of M requested pages..."
  }
}
```

## Errors
- `file_not_found` — path does not exist.
- `unsupported_format` — file is not a readable PDF.
- `dependency_missing` — `pdfplumber` is not installed.
- `page_out_of_range` / `invalid_input` — bad `pages` spec.
- `extraction_failed` — pdfplumber raised while parsing.

## Examples
### Tables on page 4
Call: `pdf.extract_tables(path="/tmp/rates.pdf", pages="4")`

### All tables in the document
Call: `pdf.extract_tables(path="/tmp/rates.pdf")`

## See also
- `pdf.extract_text` — for prose content.
- `xlsx.read` — when the source is actually a spreadsheet.
- `pdf.see` — visually confirm where the tables are before extracting.
