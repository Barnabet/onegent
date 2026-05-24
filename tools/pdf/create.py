"""
PDF authoring engine for `pdf.create`.

A single entry point: ``build(spec, out_path)``. ``spec`` is the validated
``CreateParams`` model from registry.py (themed page setup + an ordered
list of element dicts). All ReportLab imports are local to keep the rest
of the pdf domain importable when reportlab is missing.

Supported element types
-----------------------
cover, title, heading, paragraph, bullets, numbered, callout, quote,
banner, kpi_row, card, columns, badges, table, chart (bar/line/pie),
diagram, timeline, shape, image, spacer, hrule, page_break.

Inline markup in any text field:
  <b>, <i>, <u>, <sub>, <super>, <br/>, <font color='#rrggbb'>...</font>,
  <link href='https://...'>text</link>.

Unicode sub/super characters are normalised to ``<sub>``/``<super>`` tags
so they render correctly with the built-in Helvetica font (see the upstream
Anthropic skill's warning about missing glyphs).
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Theme presets — colours are RGB hex.
# ---------------------------------------------------------------------------

THEMES: Dict[str, Dict[str, str]] = {
    "default": {
        "primary": "#1f3a93", "secondary": "#4a6fa5", "accent": "#f39c12",
        "text": "#1f2937", "muted": "#6b7280", "surface": "#f3f4f6",
        "border": "#d1d5db", "font": "Helvetica",
    },
    "professional": {
        "primary": "#0f3057", "secondary": "#00587a", "accent": "#008891",
        "text": "#1a1a1a", "muted": "#6b7280", "surface": "#f5f7fa",
        "border": "#cbd5e1", "font": "Helvetica",
    },
    "modern": {
        "primary": "#6366f1", "secondary": "#8b5cf6", "accent": "#ec4899",
        "text": "#111827", "muted": "#6b7280", "surface": "#f9fafb",
        "border": "#e5e7eb", "font": "Helvetica",
    },
    "minimal": {
        "primary": "#111827", "secondary": "#374151", "accent": "#6b7280",
        "text": "#111827", "muted": "#9ca3af", "surface": "#ffffff",
        "border": "#e5e7eb", "font": "Helvetica",
    },
    "vibrant": {
        "primary": "#ef4444", "secondary": "#f59e0b", "accent": "#10b981",
        "text": "#111827", "muted": "#6b7280", "surface": "#fef3c7",
        "border": "#fbbf24", "font": "Helvetica",
    },
    "dark": {
        "primary": "#60a5fa", "secondary": "#a78bfa", "accent": "#34d399",
        "text": "#f3f4f6", "muted": "#9ca3af", "surface": "#1f2937",
        "border": "#374151", "font": "Helvetica",
    },
}


# Unicode sub/super → ASCII (for use inside <sub>/<super> tags).
_SUB_MAP = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
}
_SUP_MAP = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-", "⁼": "=", "⁽": "(", "⁾": ")",
}


def _normalize_unicode_subsuper(text: str) -> str:
    """Convert runs of Unicode sub/super chars into ReportLab <sub>/<super>
    tags so they render in the built-in fonts (otherwise: black boxes)."""
    if not text:
        return text

    def repl(match: "re.Match[str]", mapping: Dict[str, str], tag: str) -> str:
        chars = "".join(mapping[c] for c in match.group(0))
        return f"<{tag}>{chars}</{tag}>"

    text = re.sub(
        f"[{''.join(re.escape(c) for c in _SUB_MAP)}]+",
        lambda m: repl(m, _SUB_MAP, "sub"),
        text,
    )
    text = re.sub(
        f"[{''.join(re.escape(c) for c in _SUP_MAP)}]+",
        lambda m: repl(m, _SUP_MAP, "super"),
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def build(spec, out_path: Path) -> Dict[str, Any]:
    """Render ``spec`` to ``out_path`` and return a result dict."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, LEGAL, LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        Image,
        KeepTogether,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.platypus.flowables import HRFlowable

    # Resolve page size.
    size_map = {"letter": LETTER, "A4": A4, "legal": LEGAL}
    pagesize = size_map.get(spec.page_size, LETTER)

    # Resolve theme.
    if isinstance(spec.theme, str):
        theme = dict(THEMES.get(spec.theme, THEMES["default"]))
    elif isinstance(spec.theme, dict):
        theme = dict(THEMES["default"])
        theme.update({k: v for k, v in spec.theme.items() if v})
    else:
        theme = dict(THEMES["default"])

    def C(hex_str: str):
        try:
            return colors.HexColor(hex_str)
        except Exception:
            return colors.HexColor("#000000")

    primary = C(theme["primary"])
    secondary = C(theme["secondary"])
    accent = C(theme["accent"])
    text_c = C(theme["text"])
    muted = C(theme["muted"])
    surface = C(theme["surface"])
    border = C(theme["border"])
    font = theme.get("font", "Helvetica")
    font_b = f"{font}-Bold"

    # ----- Styles -----
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName=font, fontSize=10.5,
        leading=15, textColor=text_c, spaceBefore=0, spaceAfter=6,
    )
    lead = ParagraphStyle("Lead", parent=body, fontSize=12.5, leading=17)
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, leading=11, textColor=muted)
    muted_p = ParagraphStyle("Muted", parent=body, textColor=muted)
    h1 = ParagraphStyle(
        "H1", parent=body, fontName=font_b, fontSize=22, leading=28,
        textColor=primary, spaceBefore=8, spaceAfter=10,
    )
    h2 = ParagraphStyle(
        "H2", parent=body, fontName=font_b, fontSize=16, leading=22,
        textColor=primary, spaceBefore=10, spaceAfter=6,
    )
    h3 = ParagraphStyle(
        "H3", parent=body, fontName=font_b, fontSize=13, leading=18,
        textColor=secondary, spaceBefore=8, spaceAfter=4,
    )
    quote_style = ParagraphStyle(
        "Quote", parent=body, fontName=f"{font}-Oblique", fontSize=11,
        leading=16, leftIndent=18, textColor=secondary,
    )
    align_map = {"left": TA_LEFT, "right": TA_RIGHT, "center": TA_CENTER, "justify": TA_JUSTIFY}

    def text_style(name: Optional[str]) -> ParagraphStyle:
        return {"body": body, "lead": lead, "small": small, "muted": muted_p}.get(name or "body", body)

    def fmt(t: Optional[str]) -> str:
        return _normalize_unicode_subsuper(t or "")

    def para(t: Optional[str], style: ParagraphStyle, align: Optional[str] = None) -> Paragraph:
        st = style
        if align and align in align_map:
            st = ParagraphStyle(style.name + "_align", parent=style, alignment=align_map[align])
        return Paragraph(fmt(t), st)

    # ----- Document with header/footer/page-number -----
    margin = spec.margin
    doc = BaseDocTemplate(
        str(out_path),
        pagesize=pagesize,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=spec.title or "", author=spec.author or "", subject=spec.subject or "",
    )
    frame_h = doc.height
    frame = Frame(margin, margin, doc.width, frame_h, id="main", showBoundary=0)

    def _hf_text(side: Any) -> Tuple[str, str, str]:
        if side is None:
            return "", "", ""
        if isinstance(side, str):
            return "", side, ""
        if isinstance(side, dict):
            return side.get("left", "") or "", side.get("center", "") or "", side.get("right", "") or ""
        return "", "", ""

    header_l, header_c, header_r = _hf_text(spec.header)
    footer_l, footer_c, footer_r = _hf_text(spec.footer)
    show_page_no = bool(spec.page_numbers)

    def draw_header_footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(font, 8.5)
        canvas.setFillColor(muted)
        y_top = pagesize[1] - margin / 2
        y_bot = margin / 2
        page_w = pagesize[0]
        if header_l: canvas.drawString(margin, y_top, header_l)
        if header_c: canvas.drawCentredString(page_w / 2, y_top, header_c)
        if header_r: canvas.drawRightString(page_w - margin, y_top, header_r)
        if footer_l: canvas.drawString(margin, y_bot, footer_l)
        if footer_c: canvas.drawCentredString(page_w / 2, y_bot, footer_c)
        if footer_r: canvas.drawRightString(page_w - margin, y_bot, footer_r)
        if show_page_no:
            canvas.drawRightString(page_w - margin, y_bot, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=draw_header_footer)])

    # ----- Element renderers -----
    story: List[Any] = []

    def render_paragraph(el: Dict[str, Any]):
        story.append(para(el.get("text", ""), text_style(el.get("style")), el.get("align")))

    def render_heading(el: Dict[str, Any]):
        level = int(el.get("level", 2))
        style = {1: h1, 2: h2, 3: h3}.get(level, h2)
        story.append(para(el.get("text", ""), style))

    def render_title(el: Dict[str, Any]):
        story.append(para(el.get("text", ""), h1, align="left"))
        if el.get("subtitle"):
            story.append(para(el["subtitle"], lead))
        story.append(HRFlowable(width="100%", thickness=1.2, color=accent, spaceBefore=4, spaceAfter=10))

    def render_cover(el: Dict[str, Any]):
        story.append(Spacer(1, inch * 1.4))
        cover_h1 = ParagraphStyle(
            "CoverH1", parent=h1, fontSize=34, leading=42,
            textColor=C(el.get("accent") or theme["primary"]),
            alignment=TA_LEFT,
        )
        story.append(Paragraph(fmt(el.get("title", "")), cover_h1))
        if el.get("subtitle"):
            sub = ParagraphStyle("CoverSub", parent=lead, fontSize=16, leading=22, textColor=secondary)
            story.append(Paragraph(fmt(el["subtitle"]), sub))
        if el.get("tagline"):
            story.append(Spacer(1, 8))
            story.append(para(el["tagline"], muted_p))
        story.append(HRFlowable(width="40%", thickness=2, color=accent, spaceBefore=18, spaceAfter=0))
        story.append(PageBreak())

    def render_bullets(el: Dict[str, Any]):
        style_name = el.get("style", "dot")
        bullet_char = {"dot": "•", "dash": "–", "check": "✓"}.get(style_name, "•")
        for item in el.get("items", []):
            story.append(Paragraph(f"{bullet_char}  {fmt(item)}", body))

    def render_numbered(el: Dict[str, Any]):
        for i, item in enumerate(el.get("items", []), 1):
            story.append(Paragraph(f"{i}.  {fmt(item)}", body))

    def render_callout(el: Dict[str, Any]):
        variant = el.get("variant", "info")
        bg_map = {
            "info": "#dbeafe", "tip": "#d1fae5", "note": "#e0e7ff",
            "success": "#d1fae5", "warning": "#fef3c7", "danger": "#fee2e2",
        }
        bar_map = {
            "info": "#3b82f6", "tip": "#10b981", "note": "#6366f1",
            "success": "#10b981", "warning": "#f59e0b", "danger": "#ef4444",
        }
        bg = C(bg_map.get(variant, "#dbeafe"))
        bar = C(bar_map.get(variant, "#3b82f6"))
        title_html = f"<b>{fmt(el.get('title') or variant.capitalize())}</b>"
        inner = [Paragraph(title_html, ParagraphStyle("CalloutT", parent=body, textColor=bar, fontName=font_b))]
        if el.get("text"):
            inner.append(Paragraph(fmt(el["text"]), body))
        t = Table([[inner]], colWidths=[doc.width - 6])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEBEFORE", (0, 0), (0, -1), 3.5, bar),
            ("BOX", (0, 0), (-1, -1), 0.5, bar),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    def render_quote(el: Dict[str, Any]):
        story.append(Paragraph(f"“{fmt(el.get('text', ''))}”", quote_style))
        if el.get("attribution"):
            story.append(Paragraph(f"— {fmt(el['attribution'])}", small))
        story.append(Spacer(1, 4))

    def render_banner(el: Dict[str, Any]):
        bg = C(el.get("color") or theme["primary"])
        title_p = Paragraph(
            fmt(el.get("text", "")),
            ParagraphStyle("BannerT", parent=body, fontName=font_b, fontSize=14,
                           leading=18, textColor=colors.white),
        )
        inner = [title_p]
        if el.get("subtitle"):
            inner.append(Paragraph(
                fmt(el["subtitle"]),
                ParagraphStyle("BannerS", parent=body, fontSize=10, textColor=colors.white),
            ))
        t = Table([[inner]], colWidths=[doc.width])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    def render_kpi_row(el: Dict[str, Any]):
        items = el.get("items", [])
        if not items:
            return
        cells: List[List[Any]] = []
        col_widths = [doc.width / len(items)] * len(items)
        row: List[Any] = []
        for kpi in items:
            color = C(kpi.get("color") or theme["primary"])
            cell = []
            cell.append(Paragraph(
                fmt(kpi.get("label", "")),
                ParagraphStyle("KPIL", parent=body, fontSize=9, textColor=muted),
            ))
            cell.append(Paragraph(
                fmt(str(kpi.get("value", ""))),
                ParagraphStyle("KPIV", parent=body, fontName=font_b, fontSize=20,
                               leading=24, textColor=color),
            ))
            if kpi.get("delta") is not None:
                cell.append(Paragraph(
                    fmt(str(kpi["delta"])),
                    ParagraphStyle("KPID", parent=body, fontSize=9, textColor=secondary),
                ))
            row.append(cell)
        cells.append(row)
        t = Table(cells, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), surface),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("BOX", (0, 0), (-1, -1), 0.5, border),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    def render_card(el: Dict[str, Any]):
        color = C(el.get("color") or theme["secondary"])
        inner: List[Any] = []
        if el.get("title"):
            inner.append(Paragraph(
                fmt(el["title"]),
                ParagraphStyle("CardT", parent=body, fontName=font_b, fontSize=12, textColor=color),
            ))
        if el.get("text"):
            inner.append(Paragraph(fmt(el["text"]), body))
        for child in el.get("children") or []:
            inner.extend(_render(child, collect=True))
        t = Table([[inner]], colWidths=[doc.width])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), surface),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("BOX", (0, 0), (-1, -1), 0.5, border),
            ("LINEABOVE", (0, 0), (-1, 0), 2, color),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    def render_columns(el: Dict[str, Any]):
        cols = el.get("columns") or []
        if not cols:
            return
        gap = float(el.get("gap", 12))
        col_widths = [(doc.width - gap * (len(cols) - 1)) / len(cols)] * len(cols)
        row: List[Any] = []
        for col_elements in cols:
            inner: List[Any] = []
            for child in col_elements:
                inner.extend(_render(child, collect=True))
            row.append(inner)
        t = Table([row], colWidths=col_widths)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), gap),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    def render_badges(el: Dict[str, Any]):
        items = el.get("items", [])
        if not items:
            return
        row: List[Any] = []
        widths: List[float] = []
        for b in items:
            txt = fmt(str(b.get("text", "")))
            color = C(b.get("color") or theme["accent"])
            badge = Table([[Paragraph(
                txt,
                ParagraphStyle("Badge", parent=body, fontName=font_b, fontSize=8.5,
                               textColor=colors.white, alignment=TA_CENTER),
            )]], colWidths=[max(40, 7 * len(txt) + 16)])
            badge.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROUNDEDCORNERS", [3, 3, 3, 3]),
            ]))
            row.append(badge)
            widths.append(max(40, 7 * len(txt) + 16) + 4)
        # Wrap in an outer table with spacers between badges.
        outer = Table([row], colWidths=widths)
        outer.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(outer)
        story.append(Spacer(1, 6))

    def render_table(el: Dict[str, Any]):
        rows = el.get("rows") or []
        if not rows:
            return
        has_header = bool(el.get("header", True))
        style_name = el.get("style", "zebra")
        aligns = el.get("aligns") or []

        # Wrap text cells in Paragraphs so they wrap nicely.
        wrapped: List[List[Any]] = []
        for r, row in enumerate(rows):
            new_row = []
            for c, cell in enumerate(row):
                if isinstance(cell, (Paragraph, Table, Image)):
                    new_row.append(cell)
                else:
                    is_header_cell = has_header and r == 0
                    st = ParagraphStyle(
                        f"Cell{r}{c}", parent=body,
                        fontName=font_b if is_header_cell else font,
                        fontSize=9.5, leading=12,
                        textColor=colors.white if is_header_cell else text_c,
                        alignment=align_map.get(aligns[c] if c < len(aligns) else "left", TA_LEFT),
                    )
                    new_row.append(Paragraph(fmt(str(cell)), st))
            wrapped.append(new_row)

        col_widths = el.get("col_widths")
        t = Table(wrapped, colWidths=col_widths, repeatRows=1 if has_header else 0)
        ts: List[Any] = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        if has_header:
            ts.append(("BACKGROUND", (0, 0), (-1, 0), primary))
        if style_name == "zebra":
            for i in range(1 if has_header else 0, len(wrapped)):
                if (i - (1 if has_header else 0)) % 2 == 1:
                    ts.append(("BACKGROUND", (0, i), (-1, i), surface))
            ts.append(("LINEBELOW", (0, -1), (-1, -1), 0.5, border))
        elif style_name == "grid":
            ts.append(("GRID", (0, 0), (-1, -1), 0.4, border))
        else:  # minimal
            ts.append(("LINEBELOW", (0, 0), (-1, 0), 0.6, border))
            ts.append(("LINEBELOW", (0, -1), (-1, -1), 0.4, border))
        t.setStyle(TableStyle(ts))
        story.append(t)
        story.append(Spacer(1, 6))

    def render_chart(el: Dict[str, Any]):
        kind = el.get("kind", "bar")
        title = el.get("title")
        if title:
            story.append(para(title, h3))
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.charts.legends import Legend
        from reportlab.graphics.charts.linecharts import HorizontalLineChart
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.shapes import Drawing, String

        height = float(el.get("height", 200))
        width = doc.width
        d = Drawing(width, height)
        data = el.get("data") or []
        labels = el.get("labels") or []
        series_names = el.get("series_names") or []
        palette = [primary, secondary, accent, C("#10b981"), C("#ef4444"), C("#a78bfa")]

        if kind == "pie":
            pie = Pie()
            pie.x = width / 2 - 80
            pie.y = 10
            pie.width = 160
            pie.height = 160
            flat = data[0] if data and isinstance(data[0], list) else data
            pie.data = list(flat)
            pie.labels = [str(l) for l in (labels or [""] * len(flat))]
            pie.slices.strokeColor = colors.white
            pie.slices.strokeWidth = 1
            for i in range(len(flat)):
                pie.slices[i].fillColor = palette[i % len(palette)]
            d.add(pie)
        elif kind == "line":
            chart = HorizontalLineChart()
            chart.x = 40
            chart.y = 30
            chart.width = width - 60
            chart.height = height - 50
            chart.data = data if (data and isinstance(data[0], list)) else [data]
            chart.categoryAxis.categoryNames = [str(l) for l in labels]
            chart.lines.strokeWidth = 1.6
            for i, _ in enumerate(chart.data):
                chart.lines[i].strokeColor = palette[i % len(palette)]
            d.add(chart)
        else:  # bar
            chart = VerticalBarChart()
            chart.x = 40
            chart.y = 30
            chart.width = width - 60
            chart.height = height - 50
            chart.data = data if (data and isinstance(data[0], list)) else [data]
            chart.categoryAxis.categoryNames = [str(l) for l in labels]
            chart.bars.strokeWidth = 0
            for i, _ in enumerate(chart.data):
                chart.bars[i].fillColor = palette[i % len(palette)]
            d.add(chart)

        story.append(d)
        if series_names:
            story.append(para(" · ".join(series_names), small))
        story.append(Spacer(1, 8))

    def render_diagram(el: Dict[str, Any]):
        from reportlab.graphics.shapes import Drawing, Rect, String, PolyLine

        nodes = el.get("nodes") or []
        edges = el.get("edges") or []
        layout = el.get("layout", "horizontal")
        if not nodes:
            return
        w_total = doc.width
        h_total = 140 if layout == "horizontal" else max(80, 60 * len(nodes))
        d = Drawing(w_total, h_total)
        positions: Dict[str, Tuple[float, float, float, float]] = {}
        node_w = 110
        node_h = 50
        if layout == "horizontal":
            gap = (w_total - node_w * len(nodes)) / max(1, len(nodes) - 1) if len(nodes) > 1 else 0
            y = h_total / 2 - node_h / 2
            for i, n in enumerate(nodes):
                x = i * (node_w + gap)
                positions[n["id"]] = (x, y, node_w, node_h)
        else:
            y_step = h_total / max(1, len(nodes))
            x = w_total / 2 - node_w / 2
            for i, n in enumerate(nodes):
                y = h_total - (i + 1) * y_step + 6
                positions[n["id"]] = (x, y, node_w, node_h)

        for n in nodes:
            x, y, w, h = positions[n["id"]]
            color = C(n.get("color") or theme["primary"])
            d.add(Rect(x, y, w, h, fillColor=color, strokeColor=color, rx=6, ry=6))
            d.add(String(
                x + w / 2, y + h / 2 - 4, fmt(str(n.get("label", n["id"]))),
                textAnchor="middle", fontName=font_b, fontSize=10, fillColor=colors.white,
            ))
        for e in edges:
            a = positions.get(e.get("from"))
            b = positions.get(e.get("to"))
            if not a or not b:
                continue
            ax, ay, aw, ah = a
            bx, by, bw, bh = b
            if layout == "horizontal":
                pts = [ax + aw, ay + ah / 2, bx, by + bh / 2]
            else:
                pts = [ax + aw / 2, ay, bx + bw / 2, by + bh]
            d.add(PolyLine(pts, strokeColor=muted, strokeWidth=1.4))
        story.append(d)
        story.append(Spacer(1, 6))

    def render_timeline(el: Dict[str, Any]):
        items = el.get("items") or []
        for i, item in enumerate(items, 1):
            bullet = Paragraph(
                f"<b>{i}.</b>",
                ParagraphStyle("TLNum", parent=body, fontName=font_b, fontSize=11, textColor=accent),
            )
            cell = [Paragraph(fmt(item.get("title", "")), ParagraphStyle(
                "TLT", parent=body, fontName=font_b, fontSize=11, textColor=primary))]
            if item.get("text"):
                cell.append(Paragraph(fmt(item["text"]), body))
            t = Table([[bullet, cell]], colWidths=[28, doc.width - 28])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, 0), 1.2, accent),
                ("LEFTPADDING", (1, 0), (1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t)

    def render_shape(el: Dict[str, Any]):
        from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect

        w = float(el.get("width", doc.width))
        h = float(el.get("height", 30))
        d = Drawing(w, h)
        kind = el.get("shape", "rect")
        fill = C(el.get("fill") or theme["primary"])
        stroke = C(el.get("color") or theme["primary"])
        if kind == "rect":
            d.add(Rect(0, 0, w, h, fillColor=fill, strokeColor=stroke))
        elif kind == "circle":
            r = min(w, h) / 2
            d.add(Circle(w / 2, h / 2, r, fillColor=fill, strokeColor=stroke))
        elif kind == "line":
            d.add(Line(0, h / 2, w, h / 2, strokeColor=stroke, strokeWidth=float(el.get("thickness", 1))))
        elif kind == "arrow":
            d.add(Line(0, h / 2, w - 10, h / 2, strokeColor=stroke, strokeWidth=1.2))
            d.add(Polygon([w - 10, h / 2 - 6, w, h / 2, w - 10, h / 2 + 6], fillColor=stroke, strokeColor=stroke))
        story.append(d)
        story.append(Spacer(1, 4))

    def render_image(el: Dict[str, Any]):
        path = el.get("path")
        if not path or not Path(path).is_file():
            story.append(para(f"[missing image: {path}]", small))
            return
        kw: Dict[str, Any] = {}
        if el.get("width"):
            kw["width"] = float(el["width"])
        if el.get("height"):
            kw["height"] = float(el["height"])
        try:
            img = Image(path, **kw) if kw else Image(path)
        except Exception as e:
            story.append(para(f"[image error: {e}]", small))
            return
        # Cap width to frame.
        if not kw.get("width") and getattr(img, "drawWidth", 0) > doc.width:
            ratio = doc.width / img.drawWidth
            img.drawWidth = doc.width
            img.drawHeight = img.drawHeight * ratio
        story.append(img)
        if el.get("caption"):
            story.append(para(el["caption"], small))
        story.append(Spacer(1, 4))

    def render_spacer(el: Dict[str, Any]):
        story.append(Spacer(1, float(el.get("height", 12))))

    def render_hrule(el: Dict[str, Any]):
        color = C(el.get("color") or theme["border"])
        story.append(HRFlowable(width="100%", thickness=0.6, color=color, spaceBefore=4, spaceAfter=4))

    def render_page_break(_el: Dict[str, Any]):
        story.append(PageBreak())

    renderers = {
        "cover": render_cover,
        "title": render_title,
        "heading": render_heading,
        "paragraph": render_paragraph,
        "bullets": render_bullets,
        "numbered": render_numbered,
        "callout": render_callout,
        "quote": render_quote,
        "banner": render_banner,
        "kpi_row": render_kpi_row,
        "card": render_card,
        "columns": render_columns,
        "badges": render_badges,
        "table": render_table,
        "chart": render_chart,
        "diagram": render_diagram,
        "timeline": render_timeline,
        "shape": render_shape,
        "image": render_image,
        "spacer": render_spacer,
        "hrule": render_hrule,
        "page_break": render_page_break,
    }

    def _render(el: Dict[str, Any], collect: bool = False):
        """Render one element. With collect=True, capture the flowables it
        appended (used by `card` / `columns` to nest children) and return
        them instead of leaving them on the global story."""
        if collect:
            saved = list(story)
            story.clear()
            renderers.get(el.get("type", ""), lambda _e: None)(el)
            collected = list(story)
            story.clear()
            story.extend(saved)
            return collected
        renderers.get(el.get("type", ""), lambda _e: None)(el)
        return []

    for el in spec.elements:
        if not isinstance(el, dict):
            continue
        _render(el)

    if not story:
        # Reportlab refuses to build an empty document.
        story.append(Spacer(1, 1))

    doc.build(story)

    # Probe the resulting page count without re-opening with another lib.
    try:
        from pypdf import PdfReader
        page_count = len(PdfReader(str(out_path)).pages)
    except Exception:
        page_count = None

    return {
        "output": str(out_path),
        "page_count": page_count,
        "size_bytes": out_path.stat().st_size,
        "element_count": len(spec.elements),
        "theme": spec.theme if isinstance(spec.theme, str) else "custom",
        "page_size": spec.page_size,
    }
