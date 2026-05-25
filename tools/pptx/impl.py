"""
`pptx` domain — read, transform, create, and visually inspect PowerPoint decks.

Mirrors the layout and conventions of the `pdf` domain:

- Every tool returns a ``ToolResult`` envelope; no exceptions escape.
- Heavy dependencies (``python-pptx``, ``pypdfium2``, ``soffice``) are
  imported / probed lazily inside the function that needs them.
- Slide numbers in tool parameters are 1-based (matching how users speak
  about them). Internally we convert to 0-based for ``python-pptx``.
- File operations never mutate the input deck — every transform writes
  to a fresh ``output`` path.
- ``pptx.see`` rasterises slides as images by going through PDF
  (``soffice --convert-to pdf`` + ``pypdfium2``), mirroring the
  ``pdf.see`` contract (max 5 slides per call).
"""

from __future__ import annotations

import base64
import io
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from runtime.tool_registry import ToolCtx, ToolError, ToolImage, ToolResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


_PPTX_SUFFIXES = (".pptx",)


def _err(code: str, message: str, retriable: bool = False) -> ToolResult:
    return ToolResult(ok=False, error=ToolError(code=code, message=message, retriable=retriable))


def _require_input(path_str: str) -> Tuple[Optional[Path], Optional[ToolResult]]:
    p = Path(path_str)
    if not p.is_file():
        return None, _err("file_not_found", f"No file at {path_str!r}.")
    if p.suffix.lower() not in _PPTX_SUFFIXES:
        return None, _err("unsupported_format", f"{p.suffix!r} is not a .pptx file.")
    return p, None


def _check_output(path_str: str, overwrite: bool) -> Tuple[Optional[Path], Optional[ToolResult]]:
    out = Path(path_str)
    if out.suffix.lower() not in _PPTX_SUFFIXES:
        return None, _err("invalid_input", "`output` must end in .pptx.")
    if out.exists() and not overwrite:
        return None, _err("output_exists", f"{path_str!r} exists; pass overwrite=true to replace.")
    return out, None


def _parse_slides(spec: Optional[str], total: int) -> Tuple[Optional[List[int]], Optional[ToolResult]]:
    """Parse a 1-based slide spec like '1,3-5,8' into a list of 0-based indices."""
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
                start, end = int(a), int(b)
            except ValueError:
                return None, _err("invalid_input", f"Bad range {chunk!r} in slides spec.")
            if start < 1 or end < start or end > total:
                return None, _err(
                    "slide_out_of_range",
                    f"Range {chunk!r} is outside 1..{total}.",
                )
            out.extend(range(start - 1, end))
        else:
            try:
                n = int(chunk)
            except ValueError:
                return None, _err("invalid_input", f"Bad slide number {chunk!r}.")
            if n < 1 or n > total:
                return None, _err(
                    "slide_out_of_range",
                    f"Slide {n} is outside 1..{total}.",
                )
            out.append(n - 1)
    if not out:
        return None, _err("invalid_input", "slides spec is empty after parsing.")
    return out, None


def _require_pptx():
    try:
        import pptx  # type: ignore  # noqa: F401
        return pptx, None
    except ImportError:
        return None, _err("dependency_missing", "python-pptx is not installed.")


def _slide_title(slide) -> Optional[str]:
    """Best-effort extraction of a slide's title text."""
    try:
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            txt = slide.shapes.title.text_frame.text or ""
            return txt.strip() or None
    except Exception:
        pass
    # Fall back to the first placeholder with text
    try:
        for ph in slide.placeholders:
            if ph.placeholder_format is not None and ph.has_text_frame:
                txt = (ph.text_frame.text or "").strip()
                if txt:
                    return txt
    except Exception:
        pass
    return None


def _shape_iter_text(shape) -> List[str]:
    """Yield text strings out of a shape, recursing into groups + tables."""
    out: List[str] = []
    try:
        # Tables
        if getattr(shape, "has_table", False) and shape.has_table:
            for row in shape.table.rows:
                row_cells = []
                for cell in row.cells:
                    txt = (cell.text_frame.text or "").strip()
                    row_cells.append(txt)
                out.append(" | ".join(row_cells))
            return out
        # Groups
        if shape.shape_type is not None and getattr(shape, "shapes", None) is not None:
            try:
                for sub in shape.shapes:
                    out.extend(_shape_iter_text(sub))
                if out:
                    return out
            except Exception:
                pass
        # Text frame
        if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
            txt = shape.text_frame.text or ""
            if txt.strip():
                out.append(txt)
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# pptx.read — metadata + per-slide overview
# ---------------------------------------------------------------------------


def read(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    src, err = _require_input(params.path)
    if err:
        return err

    from pptx import Presentation  # type: ignore
    try:
        prs = Presentation(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PPTX: {e}")

    slides_meta: List[dict] = []
    for i, slide in enumerate(prs.slides):
        slides_meta.append({
            "index": i + 1,
            "title": _slide_title(slide),
            "layout": slide.slide_layout.name if slide.slide_layout is not None else None,
            "shape_count": len(slide.shapes),
            "has_notes": bool(
                slide.has_notes_slide
                and slide.notes_slide is not None
                and (slide.notes_slide.notes_text_frame.text or "").strip()
            ),
        })

    cp = prs.core_properties
    return ToolResult(ok=True, data={
        "path": str(src),
        "slide_count": len(prs.slides),
        "slide_width_emu": int(prs.slide_width or 0),
        "slide_height_emu": int(prs.slide_height or 0),
        "slide_width_in": round((prs.slide_width or 0) / 914400, 3),
        "slide_height_in": round((prs.slide_height or 0) / 914400, 3),
        "metadata": {
            "title": cp.title or None,
            "author": cp.author or None,
            "subject": cp.subject or None,
            "keywords": cp.keywords or None,
            "category": cp.category or None,
            "comments": cp.comments or None,
            "last_modified_by": cp.last_modified_by or None,
        },
        "slides": slides_meta,
    })


# ---------------------------------------------------------------------------
# pptx.extract_text — text per slide
# ---------------------------------------------------------------------------


def extract_text(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    src, err = _require_input(params.path)
    if err:
        return err

    from pptx import Presentation  # type: ignore
    try:
        prs = Presentation(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PPTX: {e}")

    total = len(prs.slides)
    indices, perr = _parse_slides(params.slides, total)
    if perr:
        return perr

    slides_out: List[dict] = []
    for i in indices:
        slide = prs.slides[i]
        parts: List[str] = []
        for shape in slide.shapes:
            parts.extend(_shape_iter_text(shape))
        body = "\n".join(p.strip() for p in parts if p and p.strip())
        notes = ""
        if params.include_notes and slide.has_notes_slide:
            try:
                notes = (slide.notes_slide.notes_text_frame.text or "").strip()
            except Exception:
                notes = ""
        slides_out.append({
            "slide": i + 1,
            "title": _slide_title(slide),
            "text": body,
            "notes": notes,
        })

    total_chars = sum(len(s["text"]) + len(s["notes"]) for s in slides_out)
    return ToolResult(ok=True, data={
        "slide_count": len(slides_out),
        "char_count": total_chars,
        "slides": slides_out,
    })


# ---------------------------------------------------------------------------
# pptx.extract_notes — speaker notes only
# ---------------------------------------------------------------------------


def extract_notes(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    src, err = _require_input(params.path)
    if err:
        return err

    from pptx import Presentation  # type: ignore
    try:
        prs = Presentation(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PPTX: {e}")

    total = len(prs.slides)
    indices, perr = _parse_slides(params.slides, total)
    if perr:
        return perr

    out: List[dict] = []
    for i in indices:
        slide = prs.slides[i]
        notes = ""
        if slide.has_notes_slide:
            try:
                notes = (slide.notes_slide.notes_text_frame.text or "").strip()
            except Exception:
                notes = ""
        out.append({"slide": i + 1, "notes": notes})

    return ToolResult(ok=True, data={
        "slide_count": len(out),
        "slides_with_notes": sum(1 for s in out if s["notes"]),
        "slides": out,
    })


# ---------------------------------------------------------------------------
# pptx.merge — concatenate decks
# ---------------------------------------------------------------------------


def _copy_slide(dest_prs, src_slide):
    """Copy a slide from another presentation into ``dest_prs``.

    python-pptx has no public API for cross-deck slide copy, so we rebuild
    the slide on a matching layout, copying every shape's XML.
    """
    from copy import deepcopy
    from pptx.util import Emu  # noqa: F401

    # Choose a layout by name match if possible, else fall back to the first.
    src_layout_name = src_slide.slide_layout.name if src_slide.slide_layout is not None else None
    chosen_layout = None
    if src_layout_name:
        for lay in dest_prs.slide_layouts:
            if lay.name == src_layout_name:
                chosen_layout = lay
                break
    if chosen_layout is None:
        # Prefer a "Blank" layout when the named one isn't there
        for lay in dest_prs.slide_layouts:
            if lay.name and lay.name.lower() == "blank":
                chosen_layout = lay
                break
    if chosen_layout is None:
        chosen_layout = dest_prs.slide_layouts[0]

    new_slide = dest_prs.slides.add_slide(chosen_layout)

    # Remove every shape the layout pre-populated so we start clean.
    spTree = new_slide.shapes._spTree
    for sp in list(spTree):
        # Keep the non-shape elements (e.g. nvGrpSpPr, grpSpPr)
        tag = sp.tag.split("}")[-1]
        if tag in {"sp", "pic", "graphicFrame", "grpSp", "cxnSp"}:
            spTree.remove(sp)

    # Clone every shape from the source slide.
    for shape in src_slide.shapes:
        new_el = deepcopy(shape.element)
        spTree.append(new_el)

    # Copy speaker notes if any
    try:
        if src_slide.has_notes_slide:
            src_notes = src_slide.notes_slide.notes_text_frame.text or ""
            if src_notes.strip():
                new_slide.notes_slide.notes_text_frame.text = src_notes
    except Exception:
        pass

    return new_slide


def merge(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    if len(params.inputs) < 2:
        return _err("invalid_input", "Need at least 2 input PPTX files to merge.")

    out, oerr = _check_output(params.output, params.overwrite)
    if oerr:
        return oerr

    from pptx import Presentation  # type: ignore

    # Validate inputs first.
    src_paths: List[Path] = []
    for inp in params.inputs:
        sp, err = _require_input(inp)
        if err:
            return err
        src_paths.append(sp)

    # Start from a copy of the first deck so we keep its master + theme.
    try:
        dest = Presentation(str(src_paths[0]))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open {src_paths[0]!r}: {e}")

    # Append every slide from decks 2..N
    appended = 0
    for sp in src_paths[1:]:
        try:
            src_prs = Presentation(str(sp))
        except Exception as e:
            return _err("unsupported_format", f"Failed to open {str(sp)!r}: {e}")
        for slide in src_prs.slides:
            try:
                _copy_slide(dest, slide)
            except Exception as e:
                return _err("merge_failed", f"Failed to copy slide from {sp.name}: {e}")
            appended += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.save(str(out))
    except Exception as e:
        return _err("merge_failed", f"Failed to save merged deck: {e}")

    return ToolResult(ok=True, data={
        "output": str(out),
        "slide_count": len(dest.slides),
        "source_count": len(src_paths),
        "appended": appended,
    })


# ---------------------------------------------------------------------------
# pptx.split — extract a subset of slides into a new deck
# ---------------------------------------------------------------------------


def split(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    src, err = _require_input(params.path)
    if err:
        return err
    out, oerr = _check_output(params.output, params.overwrite)
    if oerr:
        return oerr

    from pptx import Presentation  # type: ignore
    try:
        src_prs = Presentation(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PPTX: {e}")

    indices, perr = _parse_slides(params.slides, len(src_prs.slides))
    if perr:
        return perr

    keep = set(indices)
    # Easiest reliable approach: clone the source, then delete the
    # slides we don't want from the underlying XML.
    import tempfile as _t
    with _t.NamedTemporaryFile(suffix=".pptx", delete=False) as fh:
        tmp_path = Path(fh.name)
    try:
        shutil.copyfile(src, tmp_path)
        dest = Presentation(str(tmp_path))
        # Build a list of (xml_slide, rel_id) to remove.
        sldIdLst = dest.slides._sldIdLst  # CT_SlideIdList
        ids = list(sldIdLst)
        # Drop the ones not in `keep`.
        for orig_idx, sldId in enumerate(ids):
            if orig_idx not in keep:
                rId = sldId.attrib.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                )
                # Drop the relationship + part to keep the file clean.
                try:
                    if rId:
                        dest.part.drop_rel(rId)
                except Exception:
                    pass
                sldIdLst.remove(sldId)
        # Re-order remaining slides to match the requested order.
        # Build a map from original index → sldId still in tree
        remaining = {orig_idx: sldId for orig_idx, sldId in enumerate(ids) if orig_idx in keep}
        # Remove all, then re-append in the order given by `indices`
        for sldId in list(sldIdLst):
            sldIdLst.remove(sldId)
        for orig_idx in indices:
            sldIdLst.append(remaining[orig_idx])

        out.parent.mkdir(parents=True, exist_ok=True)
        dest.save(str(out))
    except Exception as e:
        return _err("split_failed", f"Failed to split deck: {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return ToolResult(ok=True, data={
        "output": str(out),
        "slide_count": len(indices),
        "selected_slides": [i + 1 for i in indices],
    })


# ---------------------------------------------------------------------------
# pptx.convert — PPTX → PDF via LibreOffice
# ---------------------------------------------------------------------------


def _run_soffice_convert(src: Path, fmt: str, out_dir: Path, timeout: int) -> Tuple[Optional[Path], Optional[ToolResult]]:
    """Run ``soffice --headless --convert-to <fmt>`` and return the produced file."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None, _err(
            "dependency_missing",
            "LibreOffice (`soffice`) is required but was not found on PATH. "
            "Install with `brew install --cask libreoffice` (mac) or "
            "`apt-get install libreoffice` (debian).",
        )

    # macOS Homebrew installs a wrapper that points at LibreOffice.app;
    # if that bundle is missing or quarantined the wrapper dies with an
    # opaque exit 127/137. Detect before invoking.
    from tools.pdf.create import _check_libreoffice_app_bundle, _interpret_libreoffice_failure
    bundle_problem = _check_libreoffice_app_bundle(soffice)
    if bundle_problem:
        return None, _err("dependency_missing", bundle_problem)

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        soffice,
        "--headless",
        "--convert-to", fmt,
        "--outdir", str(out_dir),
        str(src),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=max(5, int(timeout)))
    except subprocess.TimeoutExpired:
        return None, _err("timeout", f"LibreOffice did not finish within {timeout}s.", retriable=True)
    except Exception as e:
        return None, _err("convert_failed", f"Could not invoke LibreOffice: {e}")

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        stdout = proc.stdout.decode("utf-8", "replace").strip()
        combined = (stderr + "\n" + stdout).strip()
        hint = _interpret_libreoffice_failure(proc.returncode, combined)
        return None, _err(
            "convert_failed",
            f"LibreOffice exited {proc.returncode}. {hint}\n--- stderr ---\n{combined[:800] or '(empty)'}",
        )

    produced = out_dir / f"{src.stem}.{fmt}"
    if not produced.is_file():
        # Fall back to the single file that landed.
        candidates = [c for c in out_dir.iterdir() if c.is_file()]
        if not candidates:
            return None, _err("convert_failed", "LibreOffice produced no output file.")
        produced = candidates[0]
    return produced, None


def convert(params, ctx: ToolCtx) -> ToolResult:
    src, err = _require_input(params.path)
    if err:
        return err

    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")

    with tempfile.TemporaryDirectory() as tmpd:
        produced, perr = _run_soffice_convert(src, "pdf", Path(tmpd), params.timeout_seconds)
        if perr:
            return perr
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(produced, out)

    size = out.stat().st_size
    return ToolResult(ok=True, data={
        "output": str(out),
        "size_bytes": size,
    })


# ---------------------------------------------------------------------------
# pptx.see — render up to 5 slides and inject as images
# ---------------------------------------------------------------------------


SEE_MAX_SLIDES = 5


def see(params, ctx: ToolCtx) -> ToolResult:
    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError:
        return _err("dependency_missing", "pypdfium2 is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err

    # First, figure out total slide count so we can validate the spec.
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr
    from pptx import Presentation  # type: ignore
    try:
        prs = Presentation(str(src))
    except Exception as e:
        return _err("unsupported_format", f"Failed to open PPTX: {e}")
    total = len(prs.slides)
    # Default to slide 1 only — the model rarely wants every slide rendered.
    spec = params.slides if params.slides is not None else "1"
    indices, perr = _parse_slides(spec, total)
    if perr:
        return perr
    if len(indices) > SEE_MAX_SLIDES:
        return _err(
            "too_many_slides",
            f"see can render at most {SEE_MAX_SLIDES} slides per call; requested {len(indices)}.",
        )

    # Convert the whole deck to PDF once, then render only the slides we need.
    with tempfile.TemporaryDirectory() as tmpd:
        pdf_path, cerr = _run_soffice_convert(src, "pdf", Path(tmpd), params.timeout_seconds)
        if cerr:
            return cerr

        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
        except Exception as e:
            return _err("render_failed", f"Could not open intermediate PDF: {e}")

        pdf_pages = len(pdf)
        if pdf_pages < total:
            # LibreOffice should produce one PDF page per slide; if not, the
            # mapping is uncertain — refuse rather than guess.
            return _err(
                "render_failed",
                f"Intermediate PDF has {pdf_pages} pages but deck has {total} slides.",
            )

        images: List[ToolImage] = []
        slide_meta: List[dict] = []
        try:
            for i in indices:
                try:
                    bitmap = pdf[i].render(scale=params.scale)
                    pil = bitmap.to_pil()
                    buf = io.BytesIO()
                    pil.save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                except Exception as e:
                    return _err("render_failed", f"Failed to render slide {i + 1}: {e}")
                label = f"Slide {i + 1} of {total} — {Path(src).name}"
                images.append(ToolImage(mime="image/png", b64=b64, label=label))
                slide_meta.append({"slide": i + 1, "bytes": len(b64)})
        finally:
            try:
                pdf.close()
            except Exception:
                pass

    return ToolResult(
        ok=True,
        data={
            "path": str(src),
            "slide_count": total,
            "rendered": slide_meta,
            "scale": params.scale,
        },
        images=images,
    )


# ---------------------------------------------------------------------------
# pptx.create — author a brand-new deck from a structured element list
# ---------------------------------------------------------------------------


def create(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    out = Path(params.output)
    if out.suffix.lower() != ".pptx":
        return _err("invalid_input", "`output` must end in .pptx.")
    if out.exists() and not params.overwrite:
        return _err(
            "output_exists",
            f"{params.output!r} exists; pass overwrite=true to replace.",
        )
    out.parent.mkdir(parents=True, exist_ok=True)

    if not isinstance(params.slides, list) or not params.slides:
        return _err("invalid_input", "`slides` must be a non-empty list.")

    from . import create as _engine  # local engine module

    try:
        data = _engine.build(params, out)
    except Exception as e:
        return _err("create_failed", f"PPTX build failed: {e}")
    return ToolResult(ok=True, data=data)


# ---------------------------------------------------------------------------
# pptx.from_html — render a complete HTML document to a picture-per-slide deck
# ---------------------------------------------------------------------------


def from_html(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    out = Path(params.output)
    if out.suffix.lower() != ".pptx":
        return _err("invalid_input", "`output` must end in .pptx.")
    if out.exists() and not params.overwrite:
        return _err(
            "output_exists",
            f"{params.output!r} exists; pass overwrite=true to replace.",
        )
    out.parent.mkdir(parents=True, exist_ok=True)

    if not (params.html or "").strip():
        return _err(
            "invalid_input",
            "`html` is required: pass a complete HTML document or the path "
            "to a .html/.htm file.",
        )

    image_format = (params.image_format or "png").lower()
    if image_format not in {"png", "jpeg", "jpg"}:
        return _err(
            "invalid_input",
            f"image_format must be 'png' or 'jpeg' (got {params.image_format!r}).",
        )
    if image_format == "jpg":
        image_format = "jpeg"
    if params.image_dpi < 36 or params.image_dpi > 600:
        return _err(
            "invalid_input",
            f"image_dpi must be between 36 and 600 (got {params.image_dpi}).",
        )

    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError:
        return _err("dependency_missing", "pypdfium2 is not installed.")

    from . import from_html as _engine  # local engine module

    try:
        data = _engine.build(
            params,
            out,
            pdfium=pdfium,
            image_format=image_format,
        )
    except _engine.RenderError as e:
        return _err(e.code, str(e))
    except Exception as e:
        return _err("create_failed", f"PPTX build failed: {e}")
    return ToolResult(ok=True, data=data)


# ---------------------------------------------------------------------------
# pptx.from_html_editable — HTML → native (editable) PPTX
# ---------------------------------------------------------------------------


def from_html_editable(params, ctx: ToolCtx) -> ToolResult:
    pptx_mod, derr = _require_pptx()
    if derr:
        return derr

    out = Path(params.output)
    if out.suffix.lower() != ".pptx":
        return _err("invalid_input", "`output` must end in .pptx.")
    if out.exists() and not params.overwrite:
        return _err(
            "output_exists",
            f"{params.output!r} exists; pass overwrite=true to replace.",
        )
    out.parent.mkdir(parents=True, exist_ok=True)

    if not (params.html or "").strip():
        return _err(
            "invalid_input",
            "`html` is required: pass a complete HTML document or the path "
            "to a .html/.htm file.",
        )

    from .from_html_editable import build as _ed_engine

    try:
        data = _ed_engine.build(params, out)
    except _ed_engine.BuildError as e:
        return _err(e.code, str(e))
    except Exception as e:
        return _err("create_failed", f"PPTX build failed: {e}")
    return ToolResult(ok=True, data=data)
