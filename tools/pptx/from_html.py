"""
Engine for ``pptx.from_html`` — render a complete HTML document into a
**picture-per-slide** PPTX deck.

Pipeline
--------
1. Hand the HTML to ``tools.pdf.create.render_html_to_pdf`` so the
   exact same WeasyPrint pipeline produces a paginated PDF. One PDF
   page = one slide. ``@page`` size, margins, fonts, gradients, full
   bleed — whatever the agent declared survives 1:1.
2. Open the PDF with ``pypdfium2`` and, for each page, read its
   physical size in points. That sets the slide dimensions in EMU
   (preserving the aspect ratio the agent designed for — landscape A4,
   square Instagram, 1080×1920 social, whatever).
3. Rasterise the page at ``image_dpi`` to a PIL image, save as
   PNG (default) or JPEG, drop it full-bleed onto a blank slide.
4. Attach speaker notes from ``notes[i]`` when provided.

The output is **not editable** — every slide is a single Picture
shape. That's the deal: pixel-perfect design fidelity in exchange for
losing per-shape editability. Agents who want editable shapes should
keep using ``pptx.create`` with its element DSL.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


class RenderError(Exception):
    """Raised by ``build`` when the render pipeline fails in a way the
    tool layer should surface as a typed error. ``code`` matches the
    ToolResult error code; ``args[0]`` is the human message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# A point is 1/72 inch; an EMU is 1/914400 inch. So 1 pt = 12700 EMU.
_EMU_PER_POINT = 12_700


def build(spec, out_path: Path, *, pdfium, image_format: str) -> dict:
    """Render ``spec.html`` to ``out_path`` (a .pptx path).

    ``pdfium`` is the imported ``pypdfium2`` module (passed in so the
    tool layer can give a clean ``dependency_missing`` error before we
    get here). ``image_format`` is the already-validated lower-case
    ``'png'`` or ``'jpeg'``.

    Returns the result-data dict that ``pptx.from_html`` exposes.
    """
    from pptx import Presentation  # type: ignore
    from pptx.util import Emu

    # Late imports of the PDF engine so a fresh runtime that's missing
    # WeasyPrint still gets a clean error message via the tool layer.
    from tools.pdf import create as _pdf_engine

    notes: List[Optional[str]] = list(spec.notes or [])

    with tempfile.TemporaryDirectory() as tmpd:
        tmp_dir = Path(tmpd)
        pdf_path = tmp_dir / "deck.pdf"

        # 1. HTML → PDF (shared engine).
        try:
            engine_used, warnings = _pdf_engine.render_html_to_pdf(
                spec.html,
                pdf_path,
                engine=spec.engine,
                timeout_seconds=spec.timeout_seconds,
            )
        except _pdf_engine._DependencyMissing as e:
            raise RenderError("dependency_missing", str(e))
        except ValueError as e:
            raise RenderError("invalid_input", str(e))

        # 2. Open the PDF and walk pages.
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
        except Exception as e:
            raise RenderError(
                "render_failed", f"Could not open intermediate PDF: {e}"
            )

        try:
            page_count = len(pdf)
            if page_count == 0:
                raise RenderError(
                    "render_failed",
                    "Intermediate PDF has zero pages — your HTML produced no output.",
                )

            if notes and len(notes) > page_count:
                raise RenderError(
                    "invalid_input",
                    f"`notes` has {len(notes)} entries but the rendered deck "
                    f"only has {page_count} slides. Pass at most one note per "
                    "slide (use null for slides you don't want notes on).",
                )

            prs = Presentation()
            # Slide dimensions are set per *presentation*, not per slide,
            # so we anchor the deck to page 1's size. Different page
            # sizes within one HTML doc would need separate decks — we
            # warn the agent when that happens.
            first_w_pt, first_h_pt = _page_size_points(pdf[0])
            prs.slide_width = Emu(int(round(first_w_pt * _EMU_PER_POINT)))
            prs.slide_height = Emu(int(round(first_h_pt * _EMU_PER_POINT)))

            mixed_sizes = False
            blank_layout = _blank_layout(prs)

            for idx in range(page_count):
                page = pdf[idx]
                w_pt, h_pt = _page_size_points(page)
                if (
                    abs(w_pt - first_w_pt) > 0.5
                    or abs(h_pt - first_h_pt) > 0.5
                ):
                    mixed_sizes = True

                # 3. Rasterise the page. pypdfium2's scale param is in
                # CSS pixels per PDF point; 72 dpi is the PDF baseline,
                # so scale = dpi / 72 gives the requested output DPI.
                scale = spec.image_dpi / 72.0
                bitmap = page.render(scale=scale)
                pil = bitmap.to_pil()

                # JPEG can't carry transparency; flatten on white so
                # transparent regions don't become black.
                if image_format == "jpeg" and pil.mode in ("RGBA", "LA"):
                    from PIL import Image
                    bg = Image.new("RGB", pil.size, "white")
                    bg.paste(pil, mask=pil.split()[-1])
                    pil = bg

                img_path = tmp_dir / f"page-{idx + 1:04d}.{image_format}"
                save_kwargs: dict = {}
                if image_format == "jpeg":
                    save_kwargs["quality"] = int(spec.jpeg_quality)
                    save_kwargs["optimize"] = True
                pil.save(img_path, format=image_format.upper(), **save_kwargs)

                slide = prs.slides.add_slide(blank_layout)

                # Full-bleed picture at (0,0) → slide size. We pin to
                # the *slide* dimensions (not this page's) because the
                # presentation only carries one size; mixed sizes will
                # letterbox slightly which is documented in `warnings`.
                slide.shapes.add_picture(
                    str(img_path),
                    Emu(0), Emu(0),
                    width=prs.slide_width,
                    height=prs.slide_height,
                )

                # 4. Speaker notes.
                note_text = notes[idx] if idx < len(notes) else None
                if note_text:
                    notes_tf = slide.notes_slide.notes_text_frame
                    notes_tf.text = str(note_text)
        finally:
            try:
                pdf.close()
            except Exception:
                pass

    if mixed_sizes:
        warnings.append(
            "input HTML produced pages with mixed @page sizes; the deck "
            "uses page 1's size for every slide, so later slides may be "
            "letterboxed. Use a single @page size for visually identical slides."
        )

    _apply_pptx_metadata(prs, spec)
    prs.save(str(out_path))

    return {
        "output": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "slide_count": page_count,
        "engine": engine_used,
        "image_format": image_format,
        "image_dpi": spec.image_dpi,
        "slide_width_in": round(first_w_pt / 72.0, 4),
        "slide_height_in": round(first_h_pt / 72.0, 4),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _page_size_points(page) -> Tuple[float, float]:
    """Return (width_pt, height_pt) for a pypdfium2 page.

    pypdfium2 exposes ``get_size()`` which is documented as ``(width,
    height)`` in PDF points. We round-trip through float to defend
    against any future int-vs-float api drift.
    """
    w, h = page.get_size()
    return float(w), float(h)


def _blank_layout(prs):
    """Return the deck's blank slide layout.

    python-pptx ships a default master with the standard nine layouts
    (the 7th — index 6 — is "Blank"). Falling back to the last layout
    handles any custom master that may have re-ordered them.
    """
    layouts = prs.slide_layouts
    try:
        return layouts[6]
    except IndexError:
        return layouts[-1]


def _apply_pptx_metadata(prs, spec) -> None:
    """Set core properties on the presentation when the spec provides them.

    These show up in PowerPoint → File → Info, in Finder previews, and
    in document-management systems' search indexes.
    """
    cp = prs.core_properties
    if spec.title:
        cp.title = str(spec.title)
    if spec.author:
        cp.author = str(spec.author)
    if spec.subject:
        cp.subject = str(spec.subject)
