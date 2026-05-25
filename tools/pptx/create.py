"""
PPTX authoring engine for `pptx.create`.

A single entry point: ``build(spec, out_path)``. ``spec`` is the validated
``CreateParams`` model from ``registry.py`` — a themed deck definition plus
an ordered list of slide dicts. All ``python-pptx`` imports are local so
that the rest of the pptx domain stays importable when the package is
absent.

Supported slide types (one slide per element)
---------------------------------------------
- ``cover``       title / subtitle / tagline on the primary background
- ``title``       full-bleed section divider with a single bold line
- ``content``     title + bullet list (optional notes)
- ``two_column``  title + two text columns (`left`/`right` lists)
- ``kpi``         title + 2-6 big-number KPI cards
- ``table``       title + a styled table
- ``chart``       title + bar/line/pie chart
- ``image``       title + a single image (path) with optional caption
- ``quote``       large pull-quote with attribution
- ``image_text``  image on one side + bullets / paragraph on the other
- ``conclusion``  dark closing slide with a headline

Each slide can carry ``notes`` (speaker notes). Each text field supports
plain strings only — PowerPoint formatting (bold, colour, font) comes from
the theme and the element type, not inline HTML, so the LLM can focus on
content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Theme presets — hex strings (no leading #). Mirrors the pdf.create palette
# but uses pptxgenjs-style 6-char colours (python-pptx accepts RGBColor
# constructed from r,g,b ints; we convert).
# ---------------------------------------------------------------------------


THEMES: Dict[str, Dict[str, str]] = {
    "default": {
        "primary": "1f3a93", "secondary": "4a6fa5", "accent": "f39c12",
        "text": "1f2937", "muted": "6b7280", "surface": "f3f4f6",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Calibri", "body_font": "Calibri",
    },
    "professional": {
        "primary": "0f3057", "secondary": "00587a", "accent": "008891",
        "text": "1a1a1a", "muted": "6b7280", "surface": "f5f7fa",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Calibri", "body_font": "Calibri",
    },
    "modern": {
        "primary": "6366f1", "secondary": "8b5cf6", "accent": "ec4899",
        "text": "111827", "muted": "6b7280", "surface": "f9fafb",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Calibri", "body_font": "Calibri",
    },
    "minimal": {
        "primary": "111827", "secondary": "374151", "accent": "6b7280",
        "text": "111827", "muted": "9ca3af", "surface": "ffffff",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Georgia", "body_font": "Calibri",
    },
    "vibrant": {
        "primary": "ef4444", "secondary": "f59e0b", "accent": "10b981",
        "text": "111827", "muted": "6b7280", "surface": "fef3c7",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Calibri", "body_font": "Calibri",
    },
    "dark": {
        "primary": "0f172a", "secondary": "1e293b", "accent": "38bdf8",
        "text": "f1f5f9", "muted": "94a3b8", "surface": "1e293b",
        "background": "0f172a", "on_primary": "f1f5f9",
        "header_font": "Calibri", "body_font": "Calibri",
    },
    "midnight_executive": {
        "primary": "1E2761", "secondary": "CADCFC", "accent": "FFFFFF",
        "text": "1E2761", "muted": "6b7280", "surface": "F5F7FA",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Georgia", "body_font": "Calibri",
    },
    "forest_moss": {
        "primary": "2C5F2D", "secondary": "97BC62", "accent": "F5F5F5",
        "text": "1f2937", "muted": "6b7280", "surface": "F5F5F5",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Calibri", "body_font": "Calibri",
    },
    "terracotta": {
        "primary": "B85042", "secondary": "A7BEAE", "accent": "E7E8D1",
        "text": "1f2937", "muted": "6b7280", "surface": "E7E8D1",
        "background": "ffffff", "on_primary": "ffffff",
        "header_font": "Georgia", "body_font": "Calibri",
    },
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build(spec, out_path: Path) -> dict:
    """Build the deck from ``spec`` (validated CreateParams) and write to
    ``out_path``. Returns the data payload for the tool result."""
    from pptx import Presentation  # type: ignore
    from pptx.util import Inches

    theme = _resolve_theme(spec.theme)

    prs = Presentation()
    # Layout: 16:9 widescreen (10 x 5.625 inches) by default.
    layout = (spec.layout or "16x9").lower()
    if layout == "16x10":
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(6.25)
    elif layout == "4x3":
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)
    elif layout == "wide":
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
    else:  # 16x9 default
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

    # Metadata
    cp = prs.core_properties
    if spec.title:
        cp.title = spec.title
    if spec.author:
        cp.author = spec.author
    if spec.subject:
        cp.subject = spec.subject

    slide_w = prs.slide_width
    slide_h = prs.slide_height

    # Use the blank layout for everything; we draw all chrome ourselves so
    # the visual identity is consistent.
    blank_layout = _find_blank_layout(prs)

    rendered: List[str] = []
    for i, el in enumerate(spec.slides):
        if not isinstance(el, dict):
            raise ValueError(f"slides[{i}] is not an object")
        kind = el.get("type")
        if not kind:
            raise ValueError(f"slides[{i}] is missing required `type`")
        slide = prs.slides.add_slide(blank_layout)
        try:
            _render_slide(slide, kind, el, theme, slide_w, slide_h, prs)
        except Exception as e:
            raise ValueError(f"slides[{i}] ({kind!r}): {e}") from e
        # Speaker notes
        notes = el.get("notes")
        if notes:
            try:
                slide.notes_slide.notes_text_frame.text = str(notes)
            except Exception:
                pass
        # Page-number footer (optional)
        if spec.page_numbers and kind not in {"cover"}:
            _draw_page_number(slide, i + 1, len(spec.slides), theme, slide_w, slide_h)
        rendered.append(kind)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))

    return {
        "output": str(out_path),
        "slide_count": len(rendered),
        "size_bytes": out_path.stat().st_size,
        "theme": spec.theme if isinstance(spec.theme, str) else "custom",
        "layout": layout,
        "slides_rendered": rendered,
    }


# ---------------------------------------------------------------------------
# Theme resolution + colour helpers
# ---------------------------------------------------------------------------


def _resolve_theme(theme: Any) -> Dict[str, str]:
    if isinstance(theme, str):
        if theme not in THEMES:
            raise ValueError(
                f"unknown theme {theme!r}; choose from {sorted(THEMES.keys())}"
            )
        return dict(THEMES[theme])
    if isinstance(theme, dict):
        merged = dict(THEMES["default"])
        for k, v in theme.items():
            if isinstance(v, str):
                merged[k] = v.lstrip("#").lower()
        return merged
    raise ValueError("theme must be a string or an object of hex strings")


def _rgb(hex_str: str):
    from pptx.dml.color import RGBColor
    hex_str = (hex_str or "").lstrip("#")
    if len(hex_str) != 6:
        hex_str = "000000"
    return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def _find_blank_layout(prs):
    # Layout 6 in the default master is "Blank"; fall back to last layout.
    for lay in prs.slide_layouts:
        if lay.name and lay.name.lower() == "blank":
            return lay
    return prs.slide_layouts[-1]


# ---------------------------------------------------------------------------
# Common drawing primitives
# ---------------------------------------------------------------------------


def _add_background(slide, color_hex: str, slide_w, slide_h):
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Emu
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(0), Emu(0), slide_w, slide_h)
    shape.line.fill.background()
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(color_hex)
    # Send to back: reorder the spTree element to position 2 (after the
    # required nvGrpSpPr / grpSpPr siblings).
    spTree = slide.shapes._spTree
    spTree.remove(shape._element)
    spTree.insert(2, shape._element)
    return shape


def _add_text_box(slide, text, left, top, width, height,
                  *, font_size=18, color="111827", bold=False,
                  italic=False, font_name="Calibri", align="left", valign="top"):
    from pptx.util import Pt
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {
        "top": MSO_ANCHOR.TOP,
        "middle": MSO_ANCHOR.MIDDLE,
        "bottom": MSO_ANCHOR.BOTTOM,
    }.get(valign, MSO_ANCHOR.TOP)

    p = tf.paragraphs[0]
    p.alignment = {
        "left": PP_ALIGN.LEFT,
        "center": PP_ALIGN.CENTER,
        "right": PP_ALIGN.RIGHT,
        "justify": PP_ALIGN.JUSTIFY,
    }.get(align, PP_ALIGN.LEFT)
    run = p.add_run()
    run.text = "" if text is None else str(text)
    run.font.size = Pt(font_size)
    run.font.bold = bool(bold)
    run.font.italic = bool(italic)
    run.font.name = font_name
    run.font.color.rgb = _rgb(color)
    return box


def _add_filled_rect(slide, left, top, width, height, fill_hex,
                     line_hex=None, line_width=None):
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Pt
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(fill_hex)
    if line_hex is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = _rgb(line_hex)
        if line_width is not None:
            shape.line.width = Pt(line_width)
    return shape


def _draw_title_bar(slide, title, theme, slide_w, slide_h, subtitle=None):
    """Standard top-of-slide title strip used by content slides."""
    from pptx.util import Inches, Pt
    margin = Inches(0.6)
    width = slide_w - 2 * margin
    # Title
    _add_text_box(
        slide,
        title or "",
        margin, Inches(0.4), width, Inches(0.75),
        font_size=32, bold=True, color=theme["primary"],
        font_name=theme["header_font"],
    )
    if subtitle:
        _add_text_box(
            slide,
            subtitle,
            margin, Inches(1.15), width, Inches(0.45),
            font_size=14, color=theme["muted"], font_name=theme["body_font"],
        )


def _draw_page_number(slide, n, total, theme, slide_w, slide_h):
    from pptx.util import Inches
    _add_text_box(
        slide,
        f"{n} / {total}",
        slide_w - Inches(1.2), slide_h - Inches(0.45),
        Inches(1.0), Inches(0.3),
        font_size=10, color=theme["muted"], align="right",
        font_name=theme["body_font"],
    )


# ---------------------------------------------------------------------------
# Slide renderers (dispatched by ``type``)
# ---------------------------------------------------------------------------


def _render_slide(slide, kind, el, theme, slide_w, slide_h, prs):
    fn = _RENDERERS.get(kind)
    if fn is None:
        raise ValueError(
            f"unknown slide type {kind!r}; choose from {sorted(_RENDERERS.keys())}"
        )
    # Default background (everything except cover/conclusion which paint
    # their own background)
    if kind not in {"cover", "conclusion", "quote"}:
        _add_background(slide, theme["background"], slide_w, slide_h)
    fn(slide, el, theme, slide_w, slide_h, prs)


def _render_cover(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches
    _add_background(slide, theme["primary"], slide_w, slide_h)
    # Accent stripe
    _add_filled_rect(slide, Inches(0.6), Inches(2.3), Inches(0.6), Inches(0.08),
                     theme["accent"])
    title = el.get("title") or ""
    _add_text_box(
        slide, title,
        Inches(0.6), Inches(2.5), slide_w - Inches(1.2), Inches(1.4),
        font_size=54, bold=True, color=theme["on_primary"],
        font_name=theme["header_font"],
    )
    subtitle = el.get("subtitle")
    if subtitle:
        _add_text_box(
            slide, subtitle,
            Inches(0.6), Inches(3.9), slide_w - Inches(1.2), Inches(0.6),
            font_size=22, color=theme["on_primary"], italic=True,
            font_name=theme["body_font"],
        )
    tagline = el.get("tagline")
    if tagline:
        _add_text_box(
            slide, tagline,
            Inches(0.6), slide_h - Inches(0.9), slide_w - Inches(1.2), Inches(0.4),
            font_size=12, color=theme["on_primary"], font_name=theme["body_font"],
        )


def _render_title(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches
    _add_background(slide, theme["surface"], slide_w, slide_h)
    text = el.get("text") or ""
    _add_text_box(
        slide, text,
        Inches(0.8), slide_h / 2 - Inches(0.6),
        slide_w - Inches(1.6), Inches(1.2),
        font_size=44, bold=True, color=theme["primary"],
        font_name=theme["header_font"], align="left", valign="middle",
    )
    subtitle = el.get("subtitle")
    if subtitle:
        _add_text_box(
            slide, subtitle,
            Inches(0.8), slide_h / 2 + Inches(0.55),
            slide_w - Inches(1.6), Inches(0.6),
            font_size=18, color=theme["muted"], font_name=theme["body_font"],
        )


def _render_content(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    _draw_title_bar(slide, el.get("title"), theme, slide_w, slide_h,
                    subtitle=el.get("subtitle"))

    body = el.get("body")
    bullets = el.get("bullets") or []

    top = Inches(1.75)
    height = slide_h - top - Inches(0.7)
    left = Inches(0.6)
    width = slide_w - Inches(1.2)
    if body:
        _add_text_box(
            slide, body,
            left, top, width, Inches(0.8),
            font_size=16, color=theme["text"], font_name=theme["body_font"],
        )
        top = Inches(2.65)
        height = slide_h - top - Inches(0.7)

    if bullets:
        box = slide.shapes.add_textbox(left, top, width, height)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = 0
        for i, item in enumerate(bullets):
            text = item if isinstance(item, str) else (item.get("text") or "")
            level = 0 if isinstance(item, str) else int(item.get("level") or 0)
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.alignment = PP_ALIGN.LEFT
            p.level = max(0, min(level, 4))
            run = p.add_run()
            run.text = str(text)
            run.font.size = Pt(18)
            run.font.color.rgb = _rgb(theme["text"])
            run.font.name = theme["body_font"]
            p.space_after = Pt(6)


def _render_two_column(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    _draw_title_bar(slide, el.get("title"), theme, slide_w, slide_h,
                    subtitle=el.get("subtitle"))
    gap = Inches(0.4)
    left_x = Inches(0.6)
    col_w = (slide_w - Inches(1.2) - gap) / 2
    right_x = left_x + col_w + gap
    top = Inches(1.75)
    height = slide_h - top - Inches(0.7)

    def _draw(col_data, x):
        header = col_data.get("header") if isinstance(col_data, dict) else None
        items = (col_data.get("items") if isinstance(col_data, dict) else col_data) or []
        cur_top = top
        if header:
            _add_text_box(
                slide, header,
                x, cur_top, col_w, Inches(0.5),
                font_size=20, bold=True, color=theme["primary"],
                font_name=theme["header_font"],
            )
            cur_top = top + Inches(0.55)
        box = slide.shapes.add_textbox(x, cur_top, col_w, height - (cur_top - top))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = 0
        for i, item in enumerate(items):
            text = item if isinstance(item, str) else (item.get("text") or "")
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = str(text)
            run.font.size = Pt(16)
            run.font.color.rgb = _rgb(theme["text"])
            run.font.name = theme["body_font"]
            p.space_after = Pt(4)

    _draw(el.get("left") or {}, left_x)
    _draw(el.get("right") or {}, right_x)


def _render_kpi(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches, Pt
    _draw_title_bar(slide, el.get("title"), theme, slide_w, slide_h,
                    subtitle=el.get("subtitle"))
    items = el.get("items") or []
    if not items:
        return
    n = min(len(items), 6)
    items = items[:n]

    margin = Inches(0.6)
    gap = Inches(0.25)
    total_w = slide_w - 2 * margin
    card_w = (total_w - gap * (n - 1)) / n
    card_h = Inches(2.3)
    top = (slide_h - card_h) / 2 + Inches(0.3)

    for i, item in enumerate(items):
        x = margin + (card_w + gap) * i
        bg = (item.get("color") or theme["surface"]).lstrip("#")
        # Card background
        _add_filled_rect(slide, x, top, card_w, card_h, bg,
                         line_hex=theme.get("border") or "e5e7eb", line_width=0.5)
        # Value (big number)
        value = item.get("value") or ""
        _add_text_box(
            slide, value,
            x, top + Inches(0.45), card_w, Inches(1.0),
            font_size=40, bold=True, color=theme["primary"],
            font_name=theme["header_font"], align="center",
        )
        # Label
        label = item.get("label") or ""
        _add_text_box(
            slide, label,
            x, top + Inches(1.45), card_w, Inches(0.4),
            font_size=14, color=theme["muted"],
            font_name=theme["body_font"], align="center",
        )
        delta = item.get("delta")
        if delta:
            _add_text_box(
                slide, str(delta),
                x, top + Inches(1.85), card_w, Inches(0.35),
                font_size=12, color=theme["accent"], bold=True,
                font_name=theme["body_font"], align="center",
            )


def _render_table(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    _draw_title_bar(slide, el.get("title"), theme, slide_w, slide_h,
                    subtitle=el.get("subtitle"))
    rows = el.get("rows") or []
    if not rows:
        return
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)
    margin = Inches(0.6)
    width = slide_w - 2 * margin
    top = Inches(1.85)
    avail_h = slide_h - top - Inches(0.7)
    height = min(avail_h, Inches(0.45) * n_rows + Inches(0.2))
    has_header = el.get("header", True)

    table_shape = slide.shapes.add_table(n_rows, n_cols, margin, top, width, height)
    table = table_shape.table
    for r, row in enumerate(rows):
        for c in range(n_cols):
            val = row[c] if c < len(row) else ""
            cell = table.cell(r, c)
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = str(val) if val is not None else ""
            run.font.size = Pt(13)
            run.font.name = theme["body_font"]
            if has_header and r == 0:
                run.font.bold = True
                run.font.color.rgb = _rgb(theme["on_primary"])
                cell.fill.solid()
                cell.fill.fore_color.rgb = _rgb(theme["primary"])
            else:
                run.font.color.rgb = _rgb(theme["text"])
                # Zebra striping
                cell.fill.solid()
                cell.fill.fore_color.rgb = _rgb(
                    theme["surface"] if (r % 2 == 1) else theme["background"]
                )


def _render_chart(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches, Pt
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
    _draw_title_bar(slide, el.get("title"), theme, slide_w, slide_h,
                    subtitle=el.get("subtitle"))
    kind = (el.get("kind") or "bar").lower()
    labels = el.get("labels") or []
    data = el.get("data") or []
    series_names = el.get("series_names") or [f"Series {i+1}" for i in range(len(data))]
    if not labels or not data:
        raise ValueError("chart requires `labels` and `data`.")

    cd = CategoryChartData()
    cd.categories = [str(x) for x in labels]
    for name, series in zip(series_names, data):
        cd.add_series(str(name), [float(v) for v in series])

    chart_type = {
        "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
        "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
        "barh": XL_CHART_TYPE.BAR_CLUSTERED,
        "line": XL_CHART_TYPE.LINE,
        "pie": XL_CHART_TYPE.PIE,
        "doughnut": XL_CHART_TYPE.DOUGHNUT,
        "area": XL_CHART_TYPE.AREA,
    }.get(kind, XL_CHART_TYPE.COLUMN_CLUSTERED)

    left = Inches(0.7)
    top = Inches(1.85)
    width = slide_w - Inches(1.4)
    height = slide_h - top - Inches(0.7)
    graphic_frame = slide.shapes.add_chart(chart_type, left, top, width, height, cd)
    chart = graphic_frame.chart
    chart.has_title = False
    if kind in {"pie", "doughnut"} or len(data) > 1:
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    else:
        chart.has_legend = False


def _render_image(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches
    _draw_title_bar(slide, el.get("title"), theme, slide_w, slide_h,
                    subtitle=el.get("subtitle"))
    path = el.get("path")
    if not path or not Path(path).is_file():
        raise ValueError(f"image path missing or not found: {path!r}")
    caption = el.get("caption")
    # Fit inside the body area, preserving aspect ratio by passing only width.
    margin = Inches(0.8)
    body_top = Inches(1.85)
    body_w = slide_w - 2 * margin
    body_h = slide_h - body_top - Inches(1.0 if caption else 0.7)

    pic = slide.shapes.add_picture(str(path), margin, body_top, width=body_w)
    # Scale down if too tall.
    if pic.height > body_h:
        ratio = body_h / pic.height
        pic.width = int(pic.width * ratio)
        pic.height = int(pic.height * ratio)
    # Centre horizontally
    pic.left = int((slide_w - pic.width) / 2)
    if caption:
        _add_text_box(
            slide, caption,
            margin, body_top + pic.height + Inches(0.1),
            slide_w - 2 * margin, Inches(0.45),
            font_size=12, color=theme["muted"], italic=True,
            font_name=theme["body_font"], align="center",
        )


def _render_image_text(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    _draw_title_bar(slide, el.get("title"), theme, slide_w, slide_h,
                    subtitle=el.get("subtitle"))
    path = el.get("path")
    if not path or not Path(path).is_file():
        raise ValueError(f"image_text path missing or not found: {path!r}")

    image_side = (el.get("image_side") or "left").lower()
    margin = Inches(0.6)
    gap = Inches(0.4)
    top = Inches(1.85)
    avail_h = slide_h - top - Inches(0.7)
    half_w = (slide_w - 2 * margin - gap) / 2

    if image_side == "right":
        img_x = margin + half_w + gap
        text_x = margin
    else:
        img_x = margin
        text_x = margin + half_w + gap

    pic = slide.shapes.add_picture(str(path), img_x, top, width=half_w)
    if pic.height > avail_h:
        ratio = avail_h / pic.height
        pic.width = int(pic.width * ratio)
        pic.height = int(pic.height * ratio)
    # Vertically centre image in its column
    pic.top = int(top + (avail_h - pic.height) / 2)

    # Text column
    body = el.get("body")
    bullets = el.get("bullets") or []
    box = slide.shapes.add_textbox(text_x, top, half_w, avail_h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    first = True
    if body:
        p = tf.paragraphs[0]
        first = False
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = str(body)
        run.font.size = Pt(16)
        run.font.color.rgb = _rgb(theme["text"])
        run.font.name = theme["body_font"]
        p.space_after = Pt(8)
    for item in bullets:
        text = item if isinstance(item, str) else (item.get("text") or "")
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = "• " + str(text)
        run.font.size = Pt(15)
        run.font.color.rgb = _rgb(theme["text"])
        run.font.name = theme["body_font"]
        p.space_after = Pt(4)


def _render_quote(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches
    _add_background(slide, theme["surface"], slide_w, slide_h)
    # Accent quotation mark
    _add_text_box(
        slide, "“",
        Inches(0.6), Inches(0.6), Inches(2.0), Inches(2.0),
        font_size=120, bold=True, color=theme["primary"],
        font_name=theme["header_font"],
    )
    text = el.get("text") or ""
    _add_text_box(
        slide, text,
        Inches(1.6), Inches(1.5), slide_w - Inches(2.4), Inches(3.5),
        font_size=28, italic=True, color=theme["text"],
        font_name=theme["header_font"], valign="middle",
    )
    attribution = el.get("attribution")
    if attribution:
        _add_text_box(
            slide, f"— {attribution}",
            Inches(1.6), slide_h - Inches(1.4), slide_w - Inches(2.4), Inches(0.5),
            font_size=16, color=theme["muted"], font_name=theme["body_font"],
        )


def _render_conclusion(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches
    _add_background(slide, theme["primary"], slide_w, slide_h)
    headline = el.get("title") or el.get("text") or "Thank you"
    _add_text_box(
        slide, headline,
        Inches(0.8), slide_h / 2 - Inches(0.8), slide_w - Inches(1.6), Inches(1.6),
        font_size=54, bold=True, color=theme["on_primary"],
        font_name=theme["header_font"], align="center", valign="middle",
    )
    subtitle = el.get("subtitle")
    if subtitle:
        _add_text_box(
            slide, subtitle,
            Inches(0.8), slide_h / 2 + Inches(0.9),
            slide_w - Inches(1.6), Inches(0.6),
            font_size=20, color=theme["on_primary"], italic=True,
            font_name=theme["body_font"], align="center",
        )


def _render_section_divider(slide, el, theme, slide_w, slide_h, prs):
    from pptx.util import Inches
    _add_background(slide, theme["secondary"], slide_w, slide_h)
    label = el.get("label")
    title = el.get("title") or el.get("text") or ""
    cur_top = slide_h / 2 - Inches(0.6)
    if label:
        _add_text_box(
            slide, str(label).upper(),
            Inches(0.8), cur_top - Inches(0.7), slide_w - Inches(1.6), Inches(0.45),
            font_size=14, bold=True, color=theme["accent"],
            font_name=theme["body_font"], align="left",
        )
    _add_text_box(
        slide, title,
        Inches(0.8), cur_top, slide_w - Inches(1.6), Inches(1.5),
        font_size=44, bold=True, color=theme["on_primary"],
        font_name=theme["header_font"], align="left", valign="middle",
    )


_RENDERERS = {
    "cover": _render_cover,
    "title": _render_title,
    "section": _render_section_divider,
    "content": _render_content,
    "two_column": _render_two_column,
    "kpi": _render_kpi,
    "table": _render_table,
    "chart": _render_chart,
    "image": _render_image,
    "image_text": _render_image_text,
    "quote": _render_quote,
    "conclusion": _render_conclusion,
}
