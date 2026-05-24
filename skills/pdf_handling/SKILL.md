---
name: pdf_handling
description: >
  Use this skill whenever the user gives you a `.pdf` path or asks to do
  anything with a PDF — read it, extract text or tables, look at a page,
  merge / split / rotate, encrypt or decrypt, fill a form, or OCR a scan.
  Append this skill on top of whatever pack is running; it composes cleanly
  with other skills. Do not use this skill for `.docx`, `.pptx`, or `.xlsx`
  files — there are (or will be) dedicated skills for those.
version: 0.1.0
---

# PDF handling

## When this skill applies

The user mentions a PDF file (path, attachment, or describes one) and wants
to read, transform, inspect, or fill it. Typical triggers:

- "What's in `<path>.pdf`?"
- "Extract the table on page 4 of `report.pdf`."
- "Merge these three PDFs."
- "Show me page 2 of the contract."
- "This is a scan — pull the text out."
- "Fill the W-9 with my details."
- "Strip the password from this PDF."

## Workflow

The right first move depends on what the user wants. Use this decision
table; each entry maps to a single tool call.

| User wants | First call |
|---|---|
| Quick overview ("what is this PDF?") | `pdf.read(path=...)` |
| The text body | `pdf.extract_text(path=..., pages=<optional>)` |
| Specific tables | `pdf.extract_tables(path=..., pages=<optional>)` |
| To *see* a page (charts, layout, signatures) | `pdf.see(path=..., pages="1")` (max 5 pages) |
| OCR a scanned PDF | First `pdf.extract_text` to confirm no text layer; then `pdf.ocr(path=..., lang=...)` |
| Merge | `pdf.merge(inputs=[...], output=...)` |
| Split / extract pages | `pdf.split(path=..., pages=..., output=...)` |
| Rotate | `pdf.rotate(path=..., degrees=..., pages=<optional>, output=...)` |
| Add password | `pdf.encrypt(path=..., user_password=..., output=...)` |
| Remove password | `pdf.decrypt(path=..., password=..., output=...)` |
| Inspect a form's fields | `pdf.form_fields(path=...)` |
| Fill a form | `pdf.form_fields` first, then `pdf.fill_form(values={...}, output=...)` |

### The standard sequence for "tell me about this PDF"

1. `pdf.read(path=<path>)` to get `page_count`, `encrypted`, metadata.
2. If `encrypted=true`, ask the user for the password. Do not guess.
3. Try `pdf.extract_text(path=<path>, pages="1-<min(page_count,3)>")` for a
   sample.
4. If the sample text is empty or whitespace-only, the document is almost
   certainly a scan. Call `pdf.see(path=..., pages="1")` to confirm
   visually, then fall back to `pdf.ocr` if the user wants the text.
5. Summarise what you found: page count, document title (if any), whether
   it's a scan, and a one-paragraph gist from the sample text.

### Visual inspection — `pdf.see`

- Use `pdf.see` whenever the user's question is about *appearance*: a chart,
  a stamp, a signature, the layout, "does this look right?".
- Cap each call at 5 pages. If the user wants 10, ask whether the first 5
  are the priority or split the task.
- Render at the default `scale=2.0` unless the user reports unreadable
  images, in which case bump to `3.0`.
- After the call, the images are attached to your next turn automatically.
  Reference them ("looking at page 1 of the rendered images, the chart …")
  rather than re-emitting them.

### Forms

1. Always call `pdf.form_fields(path=...)` first. If `fillable=false`, tell
   the user the PDF is not a fillable form — do not attempt `pdf.fill_form`.
2. Show the user the field names you found and ask for the values.
3. Call `pdf.fill_form(path=..., values={...}, output=...)`.
4. Offer to `pdf.see` the output so the user can verify.

### Encrypted PDFs

- `pdf.read`, `pdf.extract_text`, and other read-side tools will fail with
  `password_required` on an encrypted PDF. Surface that error to the user
  and ask for the password; do not retry blindly.
- If the user provides one, use `pdf.read(path=..., password=...)` to
  confirm, then either pass `password=...` to subsequent reads (where
  supported) or call `pdf.decrypt` once and operate on the unencrypted copy.

## Conventions

- **Page numbers are 1-based** in every tool's `pages` argument. The model
  output should also speak in 1-based numbers. Never write "index 0".
- **Page spec syntax** is `"1"`, `"1-5"`, `"1,3,7-9"`. No spaces.
- **Never overwrite the user's input file.** Always write to a new `output`
  path. If the user explicitly asks to replace, pass `overwrite=true` but
  warn them once in the reply.
- **Output paths**: prefer the same directory as the input, with a suffix
  like `-merged.pdf`, `-rotated.pdf`, `-pages-1-5.pdf`. If the user did not
  specify, propose one and proceed.
- **OCR is a last resort.** It is slow, lossy, and language-sensitive. Try
  `pdf.extract_text` first; if it returns empty/whitespace, confirm with
  `pdf.see`, then call `pdf.ocr` with the right `lang=`.
- **Big PDFs**: if `page_count > 50` and the user did not narrow, summarise
  the document with the first few pages and ask which range they care about
  before extracting everything.

## Edge cases

- **`file_not_found`**: ask the user for a corrected path; do not list
  files or guess.
- **`unsupported_format`**: the file is not a PDF or is corrupt. Suggest
  the user verify the file; if the extension is `.docx`/`.pptx`/`.xlsx`,
  point them at the right skill.
- **`dependency_missing`** on `pdf.extract_tables`, `pdf.ocr`, or `pdf.see`:
  tell the user the runtime is missing `pdfplumber` / `pytesseract` /
  `pypdfium2`. Do not retry.
- **`page_out_of_range`**: re-read with `pdf.read` to get the true page
  count, then re-issue with a valid range.
- **`too_many_pages`** from `pdf.see`: split the request into ≤5-page calls
  or ask which 5 pages matter most.
- **`no_form_fields`** from `pdf.fill_form`: the PDF is a flat form, not a
  fillable one. Tell the user and stop; do not attempt to overlay text.
- **`password_required`**: do not retry with guessed passwords. Ask once.

## References

- The Anthropic upstream `pdf` skill (in `anthropic-skills/skills/pdf/`)
  documents the underlying Python libraries (pypdf, pdfplumber, reportlab,
  pypdfium2). This skill exposes those capabilities as tool calls; do not
  shell out or write Python yourself.
