"""Orchestrator: HTML → extractor JSON → python-pptx file.

Mirrors the shape of ``tools.pptx.from_html.build`` so the impl layer
in ``tools/pptx/impl.py`` can dispatch to either engine with the same
error-handling shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from . import extractor as _extractor
from . import mapper as _mapper


class BuildError(Exception):
    """Maps onto a typed ToolResult error in the impl layer."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def build(spec, out_path: Path) -> dict:
    """Render ``spec.html`` to an editable ``out_path`` .pptx.

    Returns the result-data dict that the tool exposes.
    """
    from pptx import Presentation  # type: ignore
    from pptx.util import Emu

    html_str, base_url = _extractor.resolve_html_input(spec.html)

    # 1. Browser extraction.
    try:
        slides_json = _extractor.extract(
            html_str,
            base_url=base_url,
            timeout_seconds=spec.timeout_seconds,
        )
    except _extractor.ExtractorError as e:
        raise BuildError(e.code, str(e))

    notes: List[Optional[str]] = list(spec.notes or [])
    if notes and len(notes) > len(slides_json):
        raise BuildError(
            "invalid_input",
            f"`notes` has {len(notes)} entries but the HTML only "
            f"produced {len(slides_json)} slides.",
        )

    # 2. Build the deck.
    prs = Presentation()
    # Slide dimensions come from the first slide's CSS pixel size.
    # 1 inch = 96 px; python-pptx Emu is 9525 per px.
    first = slides_json[0]
    prs.slide_width = Emu(int(round(first["width"] * 9525)))
    prs.slide_height = Emu(int(round(first["height"] * 9525)))

    blank = _blank_layout(prs)
    warnings: List[str] = []

    mixed_sizes = False
    for idx, sl in enumerate(slides_json):
        if (
            abs(sl["width"] - first["width"]) > 0.5
            or abs(sl["height"] - first["height"]) > 0.5
        ):
            mixed_sizes = True

        slide = prs.slides.add_slide(blank)
        _mapper.render_slide(slide, sl["atoms"])

        note_text = notes[idx] if idx < len(notes) else None
        if note_text:
            slide.notes_slide.notes_text_frame.text = str(note_text)

    if mixed_sizes:
        warnings.append(
            "HTML produced slides with mixed sizes; deck uses the "
            "first slide's size for every slide. Make all .slide "
            "containers the same width/height for consistent output."
        )

    _apply_metadata(prs, spec)
    prs.save(str(out_path))

    return {
        "output": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "slide_count": len(slides_json),
        "engine": "playwright",
        "editable": True,
        "slide_width_in": round(first["width"] / 96.0, 4),
        "slide_height_in": round(first["height"] / 96.0, 4),
        "warnings": warnings,
    }


def _blank_layout(prs):
    layouts = prs.slide_layouts
    try:
        return layouts[6]
    except IndexError:
        return layouts[-1]


def _apply_metadata(prs, spec) -> None:
    cp = prs.core_properties
    if spec.title:
        cp.title = str(spec.title)
    if spec.author:
        cp.author = str(spec.author)
    if spec.subject:
        cp.subject = str(spec.subject)
