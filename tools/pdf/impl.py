"""
`pdf` domain — read, transform, create, and visually inspect PDFs.

Design notes
------------
- Every tool returns a ``ToolResult`` envelope; no exceptions escape.
- Heavy dependencies (`pdfplumber`, `pypdfium2`, `pytesseract`, `pdf2image`)
  are imported lazily inside the function that needs them, so the rest of
  the catalog keeps loading when one is missing.
- Page numbers in tool parameters are 1-based (the way users speak about
  them). Internally we convert to 0-based for the libraries.
- File operations only ever read the input path and write to the requested
  output path. Tools never mutate the input in place.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import List, Optional, Tuple

from runtime.tool_registry import ToolCtx, ToolError, ToolImage, ToolResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _err(code: str, message: str, retriable: bool = False) -> ToolResult:
    return ToolResult(ok=False, error=ToolError(code=code, message=message, retriable=retriable))


def _require_input(path_str: str) -> Tuple[Optional[Path], Optional[ToolResult]]:
    p = Path(path_str)
    if not p.is_file():
        return None, _err("file_not_found", f"No file at {path_str!r}.")
    if p.suffix.lower() != ".pdf":
        return None, _err("unsupported_format", f"{p.suffix!r} is not a .pdf file.")
    return p, None


def _parse_pages(spec: Optional[str], total: int) -> Tuple[Optional[List[int]], Optional[ToolResult]]:
    """Parse a 1-based page spec like '1,3-5,8' into a list of 0-based indices.

    Returns (indices, None) on success, (None, ToolResult-error) on failure.
    `spec=None` means *all pages*.
    """
    if spec is None:
        return list(range(total)), None
    out: List[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, _, b = chunk.partition("-")
            try:
                start = int(a)
                end = int(b)
            except ValueError:
                return None, _err("invalid_input", f"Bad range {chunk!r} in pages spec.")
            if start < 1 or end < start or end > total:
                return None, _err(
                    "page_out_of_range",
                    f"Range {chunk!r} is outside 1..{total}.",
                )
            out.extend(range(start - 1, end))
        else:
            try:
                n = int(chunk)
            except ValueError:
                return None, _err("invalid_input", f"Bad page number {chunk!r}.")
            if n < 1 or n > total:
                return None, _err(
                    "page_out_of_range",
                    f"Page {n} is outside 1..{total}.",
                )
            out.append(n - 1)
    if not out:
        return None, _err("invalid_input", "pages spec is empty after parsing.")
    return out, None


# ---------------------------------------------------------------------------
# pdf.read — metadata + structure
# ---------------------------------------------------------------------------


def read(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err

    try:
        reader = PdfReader(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    encrypted = bool(getattr(reader, "is_encrypted", False))
    if encrypted:
        if params.password is None:
            # Caller passed no password. Report the encrypted status and
            # bail out before touching pages or metadata (pypdf raises on
            # both against an undecrypted reader).
            return ToolResult(ok=True, data={
                "path": str(src),
                "page_count": None,
                "encrypted": True,
                "metadata": None,
                "pages": [],
            })
        try:
            ok = reader.decrypt(params.password)
        except Exception:
            ok = 0
        if not ok:
            return _err("password_required", "Provided password did not unlock the PDF.")
        encrypted = False

    pages = []
    for i, page in enumerate(reader.pages):
        box = page.mediabox
        pages.append({
            "index": i + 1,
            "width": float(box.width),
            "height": float(box.height),
            "rotation": int(getattr(page, "rotation", 0) or 0),
        })

    meta = reader.metadata or {}
    return ToolResult(ok=True, data={
        "path": str(src),
        "page_count": len(reader.pages) if not encrypted else None,
        "encrypted": encrypted,
        "metadata": {
            "title": getattr(meta, "title", None),
            "author": getattr(meta, "author", None),
            "subject": getattr(meta, "subject", None),
            "creator": getattr(meta, "creator", None),
            "producer": getattr(meta, "producer", None),
        },
        "pages": pages,
    })


# ---------------------------------------------------------------------------
# pdf.extract_text
# ---------------------------------------------------------------------------


def extract_text(params, ctx: ToolCtx) -> ToolResult:
    src, err = _require_input(params.path)
    if err:
        return err

    # Prefer pdfplumber for layout fidelity, fall back to pypdf.
    try:
        import pdfplumber  # type: ignore
        backend = "pdfplumber"
    except ImportError:
        pdfplumber = None  # type: ignore
        backend = "pypdf"

    pages_text: List[dict] = []
    if backend == "pdfplumber":
        try:
            with pdfplumber.open(str(src)) as pdf:  # type: ignore[union-attr]
                total = len(pdf.pages)
                indices, perr = _parse_pages(params.pages, total)
                if perr:
                    return perr
                for i in indices:
                    page = pdf.pages[i]
                    txt = page.extract_text(layout=params.preserve_layout) or ""
                    pages_text.append({"page": i + 1, "text": txt})
        except Exception as e:
            return _err("extraction_failed", f"pdfplumber failed: {e}")
    else:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(src))
            total = len(reader.pages)
            indices, perr = _parse_pages(params.pages, total)
            if perr:
                return perr
            for i in indices:
                pages_text.append({"page": i + 1, "text": reader.pages[i].extract_text() or ""})
        except Exception as e:
            return _err("extraction_failed", f"pypdf failed: {e}")

    total_chars = sum(len(p["text"]) for p in pages_text)
    return ToolResult(ok=True, data={
        "backend": backend,
        "page_count": len(pages_text),
        "char_count": total_chars,
        "pages": pages_text,
    })


# ---------------------------------------------------------------------------
# pdf.extract_tables
# ---------------------------------------------------------------------------


def extract_tables(params, ctx: ToolCtx) -> ToolResult:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return _err("dependency_missing", "pdfplumber is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err

    out_tables: List[dict] = []
    try:
        with pdfplumber.open(str(src)) as pdf:
            total = len(pdf.pages)
            indices, perr = _parse_pages(params.pages, total)
            if perr:
                return perr
            for i in indices:
                page = pdf.pages[i]
                tables = page.extract_tables() or []
                for j, table in enumerate(tables):
                    out_tables.append({
                        "page": i + 1,
                        "index": j + 1,
                        "row_count": len(table),
                        "col_count": max((len(r) for r in table), default=0),
                        "rows": table,
                    })
    except Exception as e:
        return _err("extraction_failed", f"pdfplumber failed: {e}")

    return ToolResult(ok=True, data={
        "table_count": len(out_tables),
        "tables": out_tables,
    })


# ---------------------------------------------------------------------------
# pdf.merge
# ---------------------------------------------------------------------------


def merge(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    if len(params.inputs) < 2:
        return _err("invalid_input", "Need at least 2 input PDFs to merge.")

    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")

    writer = PdfWriter()
    for inp in params.inputs:
        src, err = _require_input(inp)
        if err:
            return err
        try:
            reader = PdfReader(str(src))
        except Exception as e:
            return _err("unsupported_format", f"Failed to open {inp!r}: {e}")
        for page in reader.pages:
            writer.add_page(page)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)
    return ToolResult(ok=True, data={
        "output": str(out),
        "page_count": len(writer.pages),
        "source_count": len(params.inputs),
    })


# ---------------------------------------------------------------------------
# pdf.split
# ---------------------------------------------------------------------------


def split(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err
    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")

    try:
        reader = PdfReader(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    indices, perr = _parse_pages(params.pages, len(reader.pages))
    if perr:
        return perr

    writer = PdfWriter()
    for i in indices:
        writer.add_page(reader.pages[i])

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)
    return ToolResult(ok=True, data={
        "output": str(out),
        "page_count": len(writer.pages),
        "selected_pages": [i + 1 for i in indices],
    })


# ---------------------------------------------------------------------------
# pdf.rotate
# ---------------------------------------------------------------------------


def rotate(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    if params.degrees not in (90, 180, 270, -90, -180, -270):
        return _err("invalid_input", "degrees must be one of ±90, ±180, ±270.")

    src, err = _require_input(params.path)
    if err:
        return err
    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")

    try:
        reader = PdfReader(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    indices, perr = _parse_pages(params.pages, len(reader.pages))
    if perr:
        return perr
    rotated = set(indices)

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in rotated:
            page.rotate(params.degrees)
        writer.add_page(page)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)
    return ToolResult(ok=True, data={
        "output": str(out),
        "rotated_pages": [i + 1 for i in indices],
        "degrees": params.degrees,
    })


# ---------------------------------------------------------------------------
# pdf.encrypt / pdf.decrypt
# ---------------------------------------------------------------------------


def encrypt(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err
    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")
    if not params.user_password:
        return _err("invalid_input", "user_password is required.")

    try:
        reader = PdfReader(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    owner = params.owner_password or params.user_password
    writer.encrypt(user_password=params.user_password, owner_password=owner)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)
    return ToolResult(ok=True, data={"output": str(out), "page_count": len(writer.pages)})


def decrypt(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err
    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")

    try:
        reader = PdfReader(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    if reader.is_encrypted:
        try:
            ok = reader.decrypt(params.password)
        except Exception:
            ok = 0
        if not ok:
            return _err("password_required", "Password did not unlock the PDF.")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)
    return ToolResult(ok=True, data={"output": str(out), "page_count": len(writer.pages)})


# ---------------------------------------------------------------------------
# pdf.ocr — text from scanned PDFs
# ---------------------------------------------------------------------------


def ocr(params, ctx: ToolCtx) -> ToolResult:
    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError:
        return _err("dependency_missing", "pypdfium2 is not installed.")
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # noqa: F401  (sanity import)
    except ImportError:
        return _err("dependency_missing", "pytesseract (and Pillow) are not installed.")

    src, err = _require_input(params.path)
    if err:
        return err

    try:
        pdf = pdfium.PdfDocument(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    total = len(pdf)
    indices, perr = _parse_pages(params.pages, total)
    if perr:
        return perr

    pages_text: List[dict] = []
    for i in indices:
        try:
            bitmap = pdf[i].render(scale=params.scale)
            img = bitmap.to_pil()
            text = pytesseract.image_to_string(img, lang=params.lang)
        except Exception as e:
            return _err("ocr_failed", f"OCR failed on page {i + 1}: {e}")
        pages_text.append({"page": i + 1, "text": text})

    return ToolResult(ok=True, data={
        "page_count": len(pages_text),
        "lang": params.lang,
        "pages": pages_text,
    })


# ---------------------------------------------------------------------------
# pdf.form_fields / pdf.fill_form
# ---------------------------------------------------------------------------


def form_fields(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err
    try:
        reader = PdfReader(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    fields = reader.get_form_text_fields() or {}
    all_fields = reader.get_fields() or {}

    listed: List[dict] = []
    for name, info in all_fields.items():
        listed.append({
            "name": name,
            "type": (info.get("/FT") if isinstance(info, dict) else None),
            "value": (info.get("/V") if isinstance(info, dict) else None),
        })
    return ToolResult(ok=True, data={
        "field_count": len(listed),
        "fillable": bool(listed),
        "text_fields": fields,
        "fields": listed,
    })


def fill_form(params, ctx: ToolCtx) -> ToolResult:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return _err("dependency_missing", "pypdf is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err
    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")
    if not params.values:
        return _err("invalid_input", "`values` is empty.")

    try:
        reader = PdfReader(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    if not reader.get_fields():
        return _err("no_form_fields", "PDF has no fillable form fields.")

    writer = PdfWriter(clone_from=reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, params.values)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        writer.write(fh)
    return ToolResult(ok=True, data={
        "output": str(out),
        "filled_fields": list(params.values.keys()),
    })


# ---------------------------------------------------------------------------
# pdf.see — render up to 5 pages and inject as images
# ---------------------------------------------------------------------------


SEE_MAX_PAGES = 5


def see(params, ctx: ToolCtx) -> ToolResult:
    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError:
        return _err("dependency_missing", "pypdfium2 is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err

    try:
        pdf = pdfium.PdfDocument(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PDF: {e}")

    total = len(pdf)
    # Default to page 1 only — the model rarely wants every page rendered.
    page_spec = params.pages if params.pages is not None else "1"
    indices, perr = _parse_pages(page_spec, total)
    if perr:
        return perr
    if len(indices) > SEE_MAX_PAGES:
        return _err(
            "too_many_pages",
            f"see can render at most {SEE_MAX_PAGES} pages per call; requested {len(indices)}.",
        )

    images: List[ToolImage] = []
    page_meta: List[dict] = []
    for i in indices:
        try:
            bitmap = pdf[i].render(scale=params.scale)
            pil = bitmap.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception as e:
            return _err("render_failed", f"Failed to render page {i + 1}: {e}")
        label = f"Page {i + 1} of {total} — {Path(src).name}"
        images.append(ToolImage(mime="image/png", b64=b64, label=label))
        page_meta.append({"page": i + 1, "bytes": len(b64)})

    return ToolResult(
        ok=True,
        data={
            "path": str(src),
            "page_count": total,
            "rendered": page_meta,
            "scale": params.scale,
        },
        images=images,
    )
