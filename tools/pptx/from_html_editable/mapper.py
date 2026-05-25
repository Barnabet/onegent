"""Turn extractor atoms into native ``python-pptx`` shapes.

The mapper is intentionally a flat ``for atom in slide["atoms"]`` loop
with one handler per atom type. Adding new visual features means
either teaching the extractor to emit a new atom kind (preferred) or
extending the corresponding ``_render_*`` here.

Unit conventions
----------------
- Extractor coordinates are CSS pixels (1px = 1/96 inch).
- python-pptx uses EMU internally; we convert via ``Emu(px * 9525)``.
- Font sizes from the extractor are already in points.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse
from urllib.request import urlopen


# 1 inch = 914400 EMU = 96 CSS pixels  →  1 px = 9525 EMU.
_EMU_PER_PX = 9525


def _emu(px: float) -> int:
    return int(round(px * _EMU_PER_PX))


def _rgb(c: Dict[str, int]):
    from pptx.dml.color import RGBColor  # type: ignore

    return RGBColor(int(c["r"]), int(c["g"]), int(c["b"]))


def _set_alpha(fill, color: Dict[str, Any]) -> None:
    """Apply the colour's alpha channel to a SolidFill by mutating
    XML. python-pptx exposes ``fill.fore_color.rgb`` but no alpha
    setter for solid fills, so we patch the underlying ``<a:srgbClr>``
    with a child ``<a:alpha val="...">`` element.
    """
    a = color.get("a", 1)
    if a is None or a >= 1:
        return
    from pptx.oxml.ns import qn

    srgb = fill._xPr.find(".//" + qn("a:srgbClr"))
    if srgb is None:
        return
    # 0..100000 per OOXML alpha-percentage scale.
    pct = max(0, min(100000, int(round(a * 100000))))
    alpha_el = srgb.find(qn("a:alpha"))
    if alpha_el is None:
        from lxml import etree

        alpha_el = etree.SubElement(srgb, qn("a:alpha"))
    alpha_el.set("val", str(pct))


# ---------------------------------------------------------------------------
# Image loading (http(s), data:, file:, plain path)
# ---------------------------------------------------------------------------


def _load_image_bytes(src: str) -> bytes | None:
    """Return raw bytes for an image src, or ``None`` if we can't get
    it. Supports data URIs, file:// URLs, http(s)://, and bare paths."""
    if not src:
        return None
    if src.startswith("data:"):
        m = re.match(r"data:[^;]+;base64,(.+)", src, re.DOTALL)
        if not m:
            return None
        try:
            return base64.b64decode(m.group(1))
        except Exception:
            return None
    parsed = urlparse(src)
    if parsed.scheme in ("http", "https"):
        try:
            with urlopen(src, timeout=10) as r:  # noqa: S310 — trusted HTML input
                return r.read()
        except Exception:
            return None
    if parsed.scheme == "file":
        try:
            return Path(parsed.path).read_bytes()
        except Exception:
            return None
    # Bare path
    try:
        return Path(src).read_bytes()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Per-atom renderers
# ---------------------------------------------------------------------------


def _render_box(slide, atom: Dict[str, Any]) -> None:
    from pptx.util import Emu
    from pptx.enum.shapes import MSO_SHAPE

    radius_px = atom.get("radius", 0) or 0
    shape_type = (
        MSO_SHAPE.ROUNDED_RECTANGLE if radius_px > 0 else MSO_SHAPE.RECTANGLE
    )

    shape = slide.shapes.add_shape(
        shape_type,
        Emu(_emu(atom["x"])),
        Emu(_emu(atom["y"])),
        Emu(_emu(atom["w"])),
        Emu(_emu(atom["h"])),
    )

    # Tune the corner radius: PowerPoint's rounded-rect "adj" value
    # is the radius as a fraction of the shorter side / 2 (0..50000).
    if radius_px > 0:
        short_side_px = min(atom["w"], atom["h"]) or 1
        # CSS radius is from the corner; PPTX "adj" is a fraction of
        # half the shorter side. Clamp at the spec maximum.
        adj = min(50000, int(round((radius_px / (short_side_px / 2)) * 50000)))
        try:
            shape.adjustments[0] = adj / 100000
        except Exception:
            pass

    # Fill.
    grad = atom.get("gradient")
    fill_color = atom.get("fill")
    fill = shape.fill
    if grad:
        _apply_linear_gradient(shape, grad)
    elif fill_color:
        fill.solid()
        fill.fore_color.rgb = _rgb(fill_color)
        _set_alpha(fill, fill_color)
    else:
        fill.background()

    # Border.
    border = atom.get("border")
    if border:
        line = shape.line
        line.color.rgb = _rgb(border["color"])
        line.width = Emu(_emu(border["width"]))
    else:
        shape.line.fill.background()

    # Opacity (whole shape). For solid fills we already applied alpha;
    # for gradients we mutate every stop. For images we'd need a
    # different path — not applicable here.
    op = atom.get("opacity", 1)
    if op < 1 and grad:
        _scale_gradient_alpha(shape, op)

    rot = atom.get("rotation", 0)
    if rot:
        shape.rotation = float(rot)


def _apply_linear_gradient(shape, grad: Dict[str, Any]) -> None:
    """Replace the shape's fill XML with a ``<a:gradFill>`` block.
    python-pptx has no high-level gradient API for arbitrary stop
    lists, so we go straight to lxml."""
    from lxml import etree
    from pptx.oxml.ns import qn

    sp_pr = shape.fill._xPr
    # Remove any existing fill children.
    for child in list(sp_pr):
        tag = etree.QName(child).localname
        if tag in {
            "noFill",
            "solidFill",
            "gradFill",
            "blipFill",
            "pattFill",
        }:
            sp_pr.remove(child)

    grad_el = etree.SubElement(sp_pr, qn("a:gradFill"))
    grad_el.set("flip", "none")
    grad_el.set("rotWithShape", "1")
    gs_lst = etree.SubElement(grad_el, qn("a:gsLst"))
    for stop in grad["stops"]:
        gs = etree.SubElement(gs_lst, qn("a:gs"))
        gs.set("pos", str(int(round(stop["offset"] * 100000))))
        c = stop["color"]
        srgb = etree.SubElement(gs, qn("a:srgbClr"))
        srgb.set(
            "val",
            f"{int(c['r']):02X}{int(c['g']):02X}{int(c['b']):02X}",
        )
        a = c.get("a", 1)
        if a < 1:
            alpha = etree.SubElement(srgb, qn("a:alpha"))
            alpha.set("val", str(int(round(a * 100000))))
    # Linear path. CSS angle is measured clockwise from "up" (0deg =
    # to top). OOXML "ang" is measured clockwise from 3 o'clock,
    # 60000 units per degree. Conversion:
    #   ooxml_angle = (css_angle + 90) % 360
    css_angle = grad.get("angle", 180)
    ooxml_angle = (css_angle + 90) % 360
    lin = etree.SubElement(grad_el, qn("a:lin"))
    lin.set("ang", str(int(round(ooxml_angle * 60000))))
    lin.set("scaled", "0")


def _scale_gradient_alpha(shape, factor: float) -> None:
    from lxml import etree
    from pptx.oxml.ns import qn

    sp_pr = shape.fill._xPr
    for srgb in sp_pr.findall(".//" + qn("a:srgbClr")):
        alpha = srgb.find(qn("a:alpha"))
        cur = int(alpha.get("val")) if alpha is not None else 100000
        new = max(0, min(100000, int(round(cur * factor))))
        if alpha is None:
            alpha = etree.SubElement(srgb, qn("a:alpha"))
        alpha.set("val", str(new))


def _render_text(slide, atom: Dict[str, Any]) -> None:
    from pptx.util import Emu, Pt
    from pptx.enum.text import PP_ALIGN

    tb = slide.shapes.add_textbox(
        Emu(_emu(atom["x"])),
        Emu(_emu(atom["y"])),
        Emu(_emu(atom["w"])),
        Emu(_emu(atom["h"])),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0

    align_map = {
        "left": PP_ALIGN.LEFT,
        "right": PP_ALIGN.RIGHT,
        "center": PP_ALIGN.CENTER,
        "justify": PP_ALIGN.JUSTIFY,
        "start": PP_ALIGN.LEFT,
        "end": PP_ALIGN.RIGHT,
    }
    align = align_map.get(atom.get("align"), PP_ALIGN.LEFT)

    # Group runs into paragraphs at <br> (text == "\n", brk=True).
    paragraphs: List[List[Dict[str, Any]]] = [[]]
    for run in atom["runs"]:
        if run.get("brk"):
            paragraphs.append([])
        else:
            paragraphs[-1].append(run)

    first = True
    for runs in paragraphs:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = align
        for run in runs:
            r = p.add_run()
            r.text = run["text"]
            r.font.name = run["font"] or "Calibri"
            r.font.size = Pt(max(1, run["size"]))
            r.font.bold = run["weight"] >= 600
            r.font.italic = bool(run.get("italic"))
            color = run.get("color")
            if color:
                r.font.color.rgb = _rgb(color)
            if "underline" in (run.get("decoration") or ""):
                r.font.underline = True


def _render_image(slide, atom: Dict[str, Any]) -> None:
    from pptx.util import Emu

    data = _load_image_bytes(atom["src"])
    if not data:
        return
    slide.shapes.add_picture(
        io.BytesIO(data),
        Emu(_emu(atom["x"])),
        Emu(_emu(atom["y"])),
        width=Emu(_emu(atom["w"])),
        height=Emu(_emu(atom["h"])),
    )


def _render_svg(slide, atom: Dict[str, Any]) -> None:
    """SVGs were screenshotted to PNG by the extractor; embed that.
    Vector EMF embedding is the planned upgrade — when we add it,
    swap this body but keep the atom contract."""
    from pptx.util import Emu

    b64 = atom.get("png_b64")
    if not b64:
        return
    try:
        data = base64.b64decode(b64)
    except Exception:
        return
    slide.shapes.add_picture(
        io.BytesIO(data),
        Emu(_emu(atom["x"])),
        Emu(_emu(atom["y"])),
        width=Emu(_emu(atom["w"])),
        height=Emu(_emu(atom["h"])),
    )


def _render_table(slide, atom: Dict[str, Any]) -> None:
    from pptx.util import Emu, Pt
    from pptx.enum.text import PP_ALIGN

    rows = atom["rows"]
    if not rows:
        return
    nrows = len(rows)
    ncols = max(len(r) for r in rows)

    table_shape = slide.shapes.add_table(
        nrows,
        ncols,
        Emu(_emu(atom["x"])),
        Emu(_emu(atom["y"])),
        Emu(_emu(atom["w"])),
        Emu(_emu(atom["h"])),
    )
    table = table_shape.table

    # Even column widths — extractor doesn't yet report per-column
    # widths, so we let PPTX distribute evenly.
    for ri, row in enumerate(rows):
        for ci, cell_atom in enumerate(row):
            cell = table.cell(ri, ci)
            tf = cell.text_frame
            tf.margin_left = tf.margin_right = Emu(_emu(4))
            tf.margin_top = tf.margin_bottom = Emu(_emu(2))

            p = tf.paragraphs[0]
            align_map = {
                "left": PP_ALIGN.LEFT,
                "right": PP_ALIGN.RIGHT,
                "center": PP_ALIGN.CENTER,
                "justify": PP_ALIGN.JUSTIFY,
            }
            p.alignment = align_map.get(cell_atom.get("align"), PP_ALIGN.LEFT)
            r = p.add_run()
            r.text = cell_atom["text"]
            r.font.name = cell_atom["font"] or "Calibri"
            r.font.size = Pt(max(1, cell_atom["size"]))
            r.font.bold = cell_atom["weight"] >= 600 or cell_atom.get("header")
            r.font.italic = bool(cell_atom.get("italic"))
            color = cell_atom.get("color")
            if color:
                r.font.color.rgb = _rgb(color)

            fill_c = cell_atom.get("fill")
            if fill_c:
                cell.fill.solid()
                cell.fill.fore_color.rgb = _rgb(fill_c)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


_RENDERERS = {
    "box": _render_box,
    "text": _render_text,
    "image": _render_image,
    "svg": _render_svg,
    "table": _render_table,
}


def render_slide(slide, atoms: List[Dict[str, Any]]) -> None:
    """Paint every atom onto a python-pptx slide, in atom order
    (already sorted by z-index in the extractor)."""
    for atom in atoms:
        renderer = _RENDERERS.get(atom.get("type"))
        if renderer is None:
            continue
        try:
            renderer(slide, atom)
        except Exception:
            # One bad atom shouldn't kill the whole deck. The build
            # function accumulates these into warnings.
            continue
