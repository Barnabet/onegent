"""
HTML authoring engine for `html.create`.

A single entry point: ``build(spec, out_path)``. ``spec`` is the validated
``CreateParams`` model from ``registry.py``: themed document settings plus
an ordered list of element dicts.

Output guarantees (the "single-file rule" from Anthropic's HTML-as-default
guidance, May 2026)
--------------------------------------------------------------------------
- One HTML file, zero external dependencies.
- All CSS lives inline in a single ``<style>`` block in ``<head>``.
- Charts are inline SVG — no JS libs, no font imports.
- Images may be passed as filesystem paths and are embedded as base64
  data URIs (no remote ``<img>`` URLs).
- System font stack only; no Google Fonts.
- A ``@media print`` block makes the document print-cleanly to PDF.
- The document is WCAG-aware: semantic headings, descriptive alt text
  required for ``image`` elements, focus-visible outlines, contrast
  designed to land ≥ 4.5:1 on every theme.

Supported element types
-----------------------
cover, title, heading, paragraph, bullets, numbered, callout (info /
tip / note / success / warning / danger), quote, banner, kpi_row, card,
columns, badges, table, chart (bar / line / pie), timeline, hrule,
spacer, image, raw_html, page_break, toc, details (collapsible).

Each text field supports a tiny safe subset of inline markup:
``<b>``, ``<i>``, ``<u>``, ``<code>``, ``<br>``, ``<a href="...">``.
Anything else is HTML-escaped.
"""

from __future__ import annotations

import base64
import html as _html
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Theme presets — hex strings. Designed for ≥ 4.5:1 contrast on body text.
# ---------------------------------------------------------------------------


THEMES: Dict[str, Dict[str, str]] = {
    "default": {
        "primary": "#1f3a93", "secondary": "#4a6fa5", "accent": "#f39c12",
        "text": "#1f2937", "muted": "#6b7280", "surface": "#f3f4f6",
        "border": "#d1d5db", "background": "#ffffff",
        "success": "#15803d", "warning": "#b45309", "danger": "#b91c1c",
        "info": "#0369a1",
    },
    "professional": {
        "primary": "#0f3057", "secondary": "#00587a", "accent": "#008891",
        "text": "#111827", "muted": "#475569", "surface": "#f5f7fa",
        "border": "#cbd5e1", "background": "#ffffff",
        "success": "#15803d", "warning": "#b45309", "danger": "#b91c1c",
        "info": "#0369a1",
    },
    "modern": {
        "primary": "#4f46e5", "secondary": "#7c3aed", "accent": "#ec4899",
        "text": "#111827", "muted": "#6b7280", "surface": "#f9fafb",
        "border": "#e5e7eb", "background": "#ffffff",
        "success": "#15803d", "warning": "#b45309", "danger": "#b91c1c",
        "info": "#0369a1",
    },
    "minimal": {
        "primary": "#111827", "secondary": "#374151", "accent": "#6b7280",
        "text": "#111827", "muted": "#6b7280", "surface": "#ffffff",
        "border": "#e5e7eb", "background": "#ffffff",
        "success": "#15803d", "warning": "#b45309", "danger": "#b91c1c",
        "info": "#0369a1",
    },
    "vibrant": {
        "primary": "#dc2626", "secondary": "#ea580c", "accent": "#059669",
        "text": "#111827", "muted": "#6b7280", "surface": "#fff7ed",
        "border": "#fbbf24", "background": "#ffffff",
        "success": "#15803d", "warning": "#b45309", "danger": "#b91c1c",
        "info": "#0369a1",
    },
    "dark": {
        "primary": "#38bdf8", "secondary": "#818cf8", "accent": "#f472b6",
        "text": "#f1f5f9", "muted": "#94a3b8", "surface": "#1e293b",
        "border": "#334155", "background": "#0f172a",
        "success": "#4ade80", "warning": "#fbbf24", "danger": "#f87171",
        "info": "#7dd3fc",
    },
}


SYSTEM_FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, '
    '"Helvetica Neue", Arial, sans-serif'
)
SYSTEM_MONO_STACK = (
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, '
    '"Liberation Mono", "Courier New", monospace'
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build(spec, out_path: Path) -> dict:
    theme = _resolve_theme(spec.theme)
    title = spec.title or "Report"

    parts: List[str] = []
    rendered: List[str] = []
    for i, el in enumerate(spec.elements):
        if not isinstance(el, dict):
            raise ValueError(f"elements[{i}] is not an object")
        kind = el.get("type")
        if not kind:
            raise ValueError(f"elements[{i}] is missing required `type`")
        fn = _RENDERERS.get(kind)
        if fn is None:
            raise ValueError(
                f"elements[{i}]: unknown type {kind!r}; choose from {sorted(_RENDERERS.keys())}"
            )
        try:
            parts.append(fn(el, theme))
        except Exception as e:
            raise ValueError(f"elements[{i}] ({kind!r}): {e}") from e
        rendered.append(kind)

    body = "\n".join(parts)
    page_header = _maybe_header_footer(spec.header, theme, "header")
    page_footer = _maybe_header_footer(spec.footer, theme, "footer")

    css = _build_css(theme, spec)
    meta_author = _attr(spec.author) if spec.author else ""
    meta_subject = _attr(spec.subject) if spec.subject else ""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(title)}</title>
<meta name="generator" content="html.create (skills-agents)">
<meta name="generated-at" content="{generated_at}">
{f'<meta name="author" content="{meta_author}">' if meta_author else ''}
{f'<meta name="description" content="{meta_subject}">' if meta_subject else ''}
<style>
{css}
</style>
</head>
<body>
{page_header}
<main class="report" id="top">
{body}
</main>
{page_footer}
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    size = out_path.stat().st_size

    return {
        "output": str(out_path),
        "size_bytes": size,
        "theme": spec.theme if isinstance(spec.theme, str) else "custom",
        "elements_rendered": rendered,
        "element_count": len(rendered),
        "self_contained": True,
    }


# ---------------------------------------------------------------------------
# Theme + CSS
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
                merged[k] = v if v.startswith("#") else f"#{v}"
        return merged
    raise ValueError("theme must be a string name or an object of hex strings")


def _build_css(theme: Dict[str, str], spec) -> str:
    max_width = int(spec.max_width or 920)
    return f""":root {{
  --primary: {theme['primary']};
  --secondary: {theme['secondary']};
  --accent: {theme['accent']};
  --text: {theme['text']};
  --muted: {theme['muted']};
  --surface: {theme['surface']};
  --border: {theme['border']};
  --background: {theme['background']};
  --success: {theme['success']};
  --warning: {theme['warning']};
  --danger: {theme['danger']};
  --info: {theme['info']};
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0;
  background: var(--background);
  color: var(--text);
  font-family: {SYSTEM_FONT_STACK};
  font-size: 16px; line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}}
.report {{
  max-width: {max_width}px;
  margin: 0 auto;
  padding: 2.25rem 1.5rem 3rem;
}}
header.page, footer.page {{
  max-width: {max_width + 80}px;
  margin: 0 auto;
  padding: 0.75rem 1.5rem;
  color: var(--muted);
  font-size: 0.85rem;
  display: flex; justify-content: space-between; gap: 1rem;
}}
header.page {{ border-bottom: 1px solid var(--border); }}
footer.page {{ border-top: 1px solid var(--border); margin-top: 2rem; }}
h1, h2, h3, h4 {{
  color: var(--primary);
  line-height: 1.2;
  margin: 2.2rem 0 0.75rem;
  font-weight: 700;
}}
h1 {{ font-size: 2.25rem; margin-top: 0; }}
h2 {{ font-size: 1.6rem; border-bottom: 2px solid var(--border); padding-bottom: 0.3rem; }}
h3 {{ font-size: 1.25rem; color: var(--secondary); }}
h4 {{ font-size: 1.05rem; color: var(--secondary); }}
p {{ margin: 0.7rem 0; }}
a {{ color: var(--primary); text-decoration: underline; text-underline-offset: 2px; }}
a:hover {{ color: var(--secondary); }}
:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 2px; border-radius: 4px; }}
code {{
  font-family: {SYSTEM_MONO_STACK};
  background: var(--surface); padding: 0.1em 0.35em; border-radius: 4px;
  font-size: 0.92em; color: var(--text);
}}
hr.rule {{
  border: 0; height: 1px; background: var(--border); margin: 2rem 0;
}}
.spacer {{ display: block; }}
ul.bullets, ol.numbered {{ margin: 0.6rem 0 0.6rem 1.4rem; padding: 0; }}
ul.bullets li, ol.numbered li {{ margin: 0.25rem 0; }}
blockquote.quote {{
  margin: 1.2rem 0; padding: 0.75rem 1.2rem;
  border-left: 4px solid var(--accent);
  background: var(--surface);
  font-style: italic; color: var(--text);
}}
blockquote.quote .attribution {{
  display: block; margin-top: 0.5rem; font-style: normal;
  color: var(--muted); font-size: 0.9rem;
}}
.cover {{
  background: var(--primary); color: #fff;
  padding: 3rem 2rem; margin: -2.25rem -1.5rem 2rem;
  border-radius: 0 0 12px 12px;
}}
.cover h1 {{ color: #fff; margin: 0; font-size: 2.6rem; }}
.cover .subtitle {{ margin-top: 0.5rem; font-size: 1.2rem; opacity: 0.92; }}
.cover .tagline {{ margin-top: 1.5rem; font-size: 0.92rem; opacity: 0.85; }}
.banner {{
  padding: 1.25rem 1.5rem; margin: 1.5rem 0; border-radius: 8px;
  background: var(--surface); border-left: 5px solid var(--primary);
}}
.banner h3 {{ margin: 0 0 0.25rem; color: var(--primary); }}
.banner .sub {{ color: var(--muted); font-size: 0.95rem; }}
.callout {{
  margin: 1.1rem 0; padding: 1rem 1.1rem; border-radius: 8px;
  border-left: 4px solid var(--info); background: var(--surface);
}}
.callout .title {{ font-weight: 700; margin-bottom: 0.25rem; color: var(--info); }}
.callout.tip     {{ border-color: var(--info);    }} .callout.tip     .title {{ color: var(--info); }}
.callout.note    {{ border-color: var(--muted);   }} .callout.note    .title {{ color: var(--muted); }}
.callout.success {{ border-color: var(--success); }} .callout.success .title {{ color: var(--success); }}
.callout.warning {{ border-color: var(--warning); }} .callout.warning .title {{ color: var(--warning); }}
.callout.danger  {{ border-color: var(--danger);  }} .callout.danger  .title {{ color: var(--danger); }}
.kpi-row {{
  display: grid; gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  margin: 1.25rem 0;
}}
.kpi {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem; text-align: center;
}}
.kpi .label {{ color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }}
.kpi .value {{ color: var(--primary); font-size: 1.9rem; font-weight: 700; margin: 0.25rem 0; }}
.kpi .delta {{ font-size: 0.85rem; font-weight: 600; }}
.kpi .delta.up   {{ color: var(--success); }}
.kpi .delta.down {{ color: var(--danger);  }}
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem 1.2rem; margin: 1rem 0;
}}
.card h3 {{ margin-top: 0; }}
.cols {{ display: grid; gap: 1rem; margin: 1.25rem 0; }}
.cols.cols-2 {{ grid-template-columns: 1fr 1fr; }}
.cols.cols-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
.cols.cols-4 {{ grid-template-columns: 1fr 1fr 1fr 1fr; }}
.badges {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.75rem 0; }}
.badge {{
  display: inline-block; padding: 0.18rem 0.6rem; border-radius: 999px;
  background: var(--surface); color: var(--text);
  border: 1px solid var(--border); font-size: 0.8rem; font-weight: 600;
}}
table.data {{
  border-collapse: collapse; width: 100%; margin: 1rem 0;
  font-size: 0.95rem;
}}
table.data th, table.data td {{
  padding: 0.55rem 0.7rem; text-align: left; border-bottom: 1px solid var(--border);
}}
table.data thead th {{
  background: var(--primary); color: #fff; font-weight: 600;
  border-bottom: none;
}}
table.data tbody tr:nth-child(even) {{ background: var(--surface); }}
table.data caption {{
  caption-side: top; text-align: left; padding: 0 0 0.4rem;
  color: var(--muted); font-size: 0.9rem;
}}
figure.chart {{ margin: 1.25rem 0; }}
figure.chart figcaption {{ color: var(--muted); font-size: 0.88rem; margin-top: 0.25rem; }}
figure.chart svg {{ width: 100%; height: auto; max-width: 100%; }}
.timeline {{ list-style: none; padding: 0; margin: 1.25rem 0; position: relative; }}
.timeline::before {{
  content: ''; position: absolute; left: 0.5rem; top: 0; bottom: 0;
  width: 2px; background: var(--border);
}}
.timeline li {{ position: relative; padding: 0.25rem 0 1rem 1.75rem; }}
.timeline li::before {{
  content: ''; position: absolute; left: 0; top: 0.5rem; width: 0.85rem; height: 0.85rem;
  background: var(--accent); border-radius: 50%; border: 2px solid var(--background);
  box-shadow: 0 0 0 1px var(--border);
}}
.timeline .when {{ display: block; color: var(--muted); font-size: 0.82rem; }}
.timeline .title {{ font-weight: 600; color: var(--text); }}
.toc {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem 1.25rem; margin: 1.25rem 0;
}}
.toc h2 {{ margin: 0 0 0.5rem; font-size: 1.05rem; border: 0; padding: 0; color: var(--text); }}
.toc ol {{ margin: 0; padding-left: 1.2rem; }}
.toc a {{ text-decoration: none; }}
.toc a:hover {{ text-decoration: underline; }}
details.collapsible {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.5rem 1rem; margin: 0.75rem 0;
}}
details.collapsible > summary {{
  cursor: pointer; font-weight: 600; color: var(--primary);
  padding: 0.4rem 0;
}}
details.collapsible[open] > summary {{ margin-bottom: 0.5rem; }}
img.embed {{ max-width: 100%; height: auto; display: block; margin: 1rem auto; border-radius: 6px; }}
figure.image figcaption {{ color: var(--muted); font-size: 0.88rem; text-align: center; margin-top: 0.25rem; }}

/* Print-ready: produces a clean A4 PDF when the user hits Print. */
@media print {{
  html, body {{ background: #fff; color: #000; font-size: 11pt; }}
  .report {{ max-width: none; margin: 0; padding: 0; }}
  header.page, footer.page {{ display: none; }}
  a {{ color: #000; text-decoration: underline; }}
  h1, h2, h3, h4 {{ color: #000; page-break-after: avoid; }}
  .cover {{ background: #000; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  table.data thead {{ display: table-header-group; }}
  tr, .kpi, .card, .callout {{ page-break-inside: avoid; }}
  .page-break {{ page-break-before: always; }}
  .toc, details.collapsible {{ break-inside: avoid; }}
  details.collapsible {{ border: none; }}
  details.collapsible > summary {{ list-style: none; }}
}}
.page-break {{ height: 0; overflow: hidden; }}
"""


def _maybe_header_footer(payload, theme: Dict[str, str], kind: str) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        left, center, right = "", payload, ""
    elif isinstance(payload, dict):
        left = payload.get("left") or ""
        center = payload.get("center") or ""
        right = payload.get("right") or ""
    else:
        return ""
    return (
        f'<{kind} class="page">'
        f'<span class="left">{_inline(left)}</span>'
        f'<span class="center">{_inline(center)}</span>'
        f'<span class="right">{_inline(right)}</span>'
        f'</{kind}>'
    )


# ---------------------------------------------------------------------------
# Escaping + inline-markup sanitiser
# ---------------------------------------------------------------------------


_ALLOWED_INLINE = {"b", "strong", "i", "em", "u", "code", "br", "a", "span"}
_INLINE_TAG_RE = re.compile(r"<(/?)(\w+)([^>]*)>", re.S)
_HREF_RE = re.compile(r'href\s*=\s*"([^"]*)"|href\s*=\s*\'([^\']*)\'', re.I)


def _escape(s: Any) -> str:
    return _html.escape("" if s is None else str(s), quote=True)


def _attr(s: Any) -> str:
    return _html.escape("" if s is None else str(s), quote=True)


def _inline(s: Any) -> str:
    """Allow a tiny safe subset of inline tags, escape everything else."""
    if s is None:
        return ""
    text = str(s)

    # Two-pass: escape entire string, then re-introduce allowed tags by
    # substituting the escaped form back.
    escaped = _html.escape(text, quote=True)
    # Restore allowed tags
    def _restore(m):
        slash, tag, rest = m.group(1), m.group(2).lower(), m.group(3)
        if tag not in _ALLOWED_INLINE:
            return m.group(0)  # leave escaped form (which won't match because of &lt;)
        if tag == "a" and not slash:
            href = ""
            href_m = _HREF_RE.search(rest)
            if href_m:
                href = href_m.group(1) or href_m.group(2) or ""
            # only allow http(s), mailto, and fragment links
            if not re.match(r"^(https?:|mailto:|#|/)", href, re.I):
                href = "#"
            return f'<a href="{_attr(href)}">'
        if tag == "br" and not slash:
            return "<br>"
        return f"<{slash}{tag}>"
    # Re-locate escaped tags like &lt;b&gt; and turn them into <b>.
    pattern = re.compile(r"&lt;(/?)(\w+)([^&]*?)&gt;")
    def _maybe_restore(m):
        slash, tag, rest = m.group(1), m.group(2).lower(), m.group(3)
        if tag not in _ALLOWED_INLINE:
            return m.group(0)
        # Unescape attrs minimally for the href detection.
        rest_unescaped = rest.replace("&quot;", '"').replace("&#x27;", "'").replace("&amp;", "&")
        if tag == "a" and not slash:
            href = ""
            href_m = _HREF_RE.search(rest_unescaped)
            if href_m:
                href = href_m.group(1) or href_m.group(2) or ""
            if not re.match(r"^(https?:|mailto:|#|/)", href, re.I):
                href = "#"
            return f'<a href="{_attr(href)}">'
        if tag == "br" and not slash:
            return "<br>"
        return f"<{slash}{tag}>"
    return pattern.sub(_maybe_restore, escaped)


# ---------------------------------------------------------------------------
# Element renderers
# ---------------------------------------------------------------------------


def _r_cover(el: dict, theme) -> str:
    title = el.get("title") or ""
    subtitle = el.get("subtitle")
    tagline = el.get("tagline")
    parts = [f'<h1>{_inline(title)}</h1>']
    if subtitle:
        parts.append(f'<div class="subtitle">{_inline(subtitle)}</div>')
    if tagline:
        parts.append(f'<div class="tagline">{_inline(tagline)}</div>')
    return f'<section class="cover">{"".join(parts)}</section>'


def _r_title(el: dict, theme) -> str:
    text = el.get("text") or el.get("title") or ""
    subtitle = el.get("subtitle")
    out = [f'<h1>{_inline(text)}</h1>']
    if subtitle:
        out.append(f'<p class="lead" style="color: var(--muted); font-size: 1.1rem;">{_inline(subtitle)}</p>')
    return "\n".join(out)


def _r_heading(el: dict, theme) -> str:
    level = int(el.get("level") or 2)
    level = max(1, min(level, 4))
    text = el.get("text") or ""
    anchor = el.get("id")
    if anchor:
        return f'<h{level} id="{_attr(anchor)}">{_inline(text)}</h{level}>'
    return f"<h{level}>{_inline(text)}</h{level}>"


def _r_paragraph(el: dict, theme) -> str:
    text = el.get("text") or ""
    style = (el.get("style") or "").lower()
    cls = ""
    if style == "lead":
        cls = ' class="lead" style="font-size:1.1rem;color:var(--text);"'
    elif style == "muted":
        cls = ' style="color:var(--muted);"'
    elif style == "small":
        cls = ' style="font-size:0.88rem;color:var(--muted);"'
    align = (el.get("align") or "").lower()
    if align in {"left", "center", "right", "justify"}:
        cls = cls.rstrip('"') + f';text-align:{align};"' if cls else f' style="text-align:{align};"'
    return f"<p{cls}>{_inline(text)}</p>"


def _r_bullets(el: dict, theme) -> str:
    items = el.get("items") or []
    lis = [f"<li>{_inline(item)}</li>" for item in items]
    return f'<ul class="bullets">{"".join(lis)}</ul>'


def _r_numbered(el: dict, theme) -> str:
    items = el.get("items") or []
    lis = [f"<li>{_inline(item)}</li>" for item in items]
    return f'<ol class="numbered">{"".join(lis)}</ol>'


def _r_callout(el: dict, theme) -> str:
    variant = (el.get("variant") or "info").lower()
    if variant not in {"info", "tip", "note", "success", "warning", "danger"}:
        variant = "info"
    title = el.get("title")
    text = el.get("text") or ""
    parts: List[str] = []
    if title:
        parts.append(f'<div class="title">{_inline(title)}</div>')
    parts.append(f"<div>{_inline(text)}</div>")
    return f'<div class="callout {variant}" role="note">{"".join(parts)}</div>'


def _r_quote(el: dict, theme) -> str:
    text = el.get("text") or ""
    attribution = el.get("attribution")
    body = f"<p>{_inline(text)}</p>"
    if attribution:
        body += f'<span class="attribution">— {_inline(attribution)}</span>'
    return f'<blockquote class="quote">{body}</blockquote>'


def _r_banner(el: dict, theme) -> str:
    text = el.get("text") or el.get("title") or ""
    subtitle = el.get("subtitle")
    out = [f"<h3>{_inline(text)}</h3>"]
    if subtitle:
        out.append(f'<div class="sub">{_inline(subtitle)}</div>')
    return f'<section class="banner">{"".join(out)}</section>'


def _r_kpi_row(el: dict, theme) -> str:
    items = el.get("items") or []
    cards = []
    for it in items:
        label = it.get("label") or ""
        value = it.get("value") or ""
        delta = it.get("delta")
        direction = (it.get("direction") or "").lower()
        delta_cls = ""
        if direction in {"up", "down"}:
            delta_cls = f" {direction}"
        elif isinstance(delta, str) and delta.strip().startswith(("+", "▲")):
            delta_cls = " up"
        elif isinstance(delta, str) and delta.strip().startswith(("-", "▼")):
            delta_cls = " down"
        delta_html = f'<div class="delta{delta_cls}">{_inline(delta)}</div>' if delta else ""
        cards.append(
            f'<div class="kpi"><div class="label">{_inline(label)}</div>'
            f'<div class="value">{_inline(value)}</div>{delta_html}</div>'
        )
    return f'<div class="kpi-row">{"".join(cards)}</div>'


def _r_card(el: dict, theme) -> str:
    title = el.get("title")
    text = el.get("text")
    children = el.get("children") or []
    parts: List[str] = []
    if title:
        parts.append(f"<h3>{_inline(title)}</h3>")
    if text:
        parts.append(f"<p>{_inline(text)}</p>")
    for child in children:
        if not isinstance(child, dict):
            continue
        kind = child.get("type")
        fn = _RENDERERS.get(kind)
        if fn:
            parts.append(fn(child, theme))
    return f'<section class="card">{"".join(parts)}</section>'


def _r_columns(el: dict, theme) -> str:
    cols = el.get("columns") or []
    if not cols:
        return ""
    n = min(max(len(cols), 1), 4)
    inner: List[str] = []
    for col in cols:
        col_parts: List[str] = []
        for child in (col or []):
            if not isinstance(child, dict):
                continue
            kind = child.get("type")
            fn = _RENDERERS.get(kind)
            if fn:
                col_parts.append(fn(child, theme))
        inner.append(f"<div>{''.join(col_parts)}</div>")
    return f'<div class="cols cols-{n}">{"".join(inner)}</div>'


def _r_badges(el: dict, theme) -> str:
    items = el.get("items") or []
    spans = []
    for it in items:
        if isinstance(it, str):
            text, color = it, None
        else:
            text = it.get("text") or ""
            color = it.get("color")
        style = ""
        if color:
            c = color if color.startswith("#") else f"#{color}"
            style = f' style="background:{_attr(c)};color:#fff;border-color:{_attr(c)};"'
        spans.append(f'<span class="badge"{style}>{_inline(text)}</span>')
    return f'<div class="badges">{"".join(spans)}</div>'


def _r_table(el: dict, theme) -> str:
    rows = el.get("rows") or []
    if not rows:
        raise ValueError("table requires `rows`")
    header = bool(el.get("header", True))
    caption = el.get("caption")
    aligns = el.get("aligns") or []

    def _cell(tag, val, idx):
        align = aligns[idx] if idx < len(aligns) else None
        st = f' style="text-align:{align};"' if align in {"left", "center", "right"} else ""
        return f"<{tag}{st}>{_inline(val)}</{tag}>"

    out = ['<table class="data">']
    if caption:
        out.append(f"<caption>{_inline(caption)}</caption>")
    if header and rows:
        head = rows[0]
        out.append("<thead><tr>" + "".join(_cell("th", v, i) for i, v in enumerate(head)) + "</tr></thead>")
        body_rows = rows[1:]
    else:
        body_rows = rows
    out.append("<tbody>")
    for row in body_rows:
        out.append("<tr>" + "".join(_cell("td", v, i) for i, v in enumerate(row)) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


# ---------------------------------------------------------------------------
# SVG charts — bar / line / pie. No external libs.
# ---------------------------------------------------------------------------


_CHART_PALETTE = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
]


def _r_chart(el: dict, theme) -> str:
    kind = (el.get("kind") or "bar").lower()
    title = el.get("title")
    labels = el.get("labels") or []
    data = el.get("data") or []
    series_names = el.get("series_names") or [f"Series {i+1}" for i in range(len(data))]
    if not labels or not data:
        raise ValueError("chart requires `labels` and `data`")

    if kind in {"bar", "column"}:
        svg = _svg_bar(labels, data, series_names, theme)
    elif kind == "line":
        svg = _svg_line(labels, data, series_names, theme)
    elif kind == "pie":
        svg = _svg_pie(labels, data[0] if data else [], theme)
    else:
        raise ValueError(f"unsupported chart kind {kind!r}; use bar/line/pie")

    caption = f"<figcaption>{_inline(title)}</figcaption>" if title else ""
    return f'<figure class="chart" role="img" aria-label="{_attr(title or kind + " chart")}">{svg}{caption}</figure>'


def _svg_bar(labels, data, series_names, theme) -> str:
    W, H = 700, 320
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 50
    n_groups = len(labels)
    n_series = len(data)
    flat = [float(v) for series in data for v in series]
    vmax = max(flat) if flat else 1.0
    vmax = vmax if vmax > 0 else 1.0
    # Y ticks
    ticks = _nice_ticks(0, vmax, 5)
    vmax = max(ticks)
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b
    group_w = chart_w / max(n_groups, 1)
    bar_w = group_w / (n_series + 1)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">']
    # Axes
    parts.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{H - pad_b}" stroke="{theme["border"]}" />')
    parts.append(f'<line x1="{pad_l}" y1="{H - pad_b}" x2="{W - pad_r}" y2="{H - pad_b}" stroke="{theme["border"]}" />')
    # Gridlines + y labels
    for t in ticks:
        y = (H - pad_b) - (t / vmax) * chart_h
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - pad_r}" y2="{y:.1f}" stroke="{theme["border"]}" stroke-dasharray="2,3" opacity="0.6" />')
        parts.append(f'<text x="{pad_l - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{theme["muted"]}">{_fmt_num(t)}</text>')
    # Bars
    for gi in range(n_groups):
        gx = pad_l + gi * group_w
        for si, series in enumerate(data):
            v = float(series[gi]) if gi < len(series) else 0.0
            x = gx + bar_w * 0.5 + si * bar_w
            h = (v / vmax) * chart_h if vmax else 0
            y = (H - pad_b) - h
            color = _CHART_PALETTE[si % len(_CHART_PALETTE)]
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w * 0.92:.1f}" height="{h:.1f}" fill="{color}" />')
        # x label
        label = str(labels[gi])
        parts.append(f'<text x="{gx + group_w / 2:.1f}" y="{H - pad_b + 18}" text-anchor="middle" font-size="11" fill="{theme["text"]}">{_escape(label)}</text>')
    # Legend
    if n_series > 1:
        lx = pad_l
        ly = H - 12
        for si, name in enumerate(series_names):
            color = _CHART_PALETTE[si % len(_CHART_PALETTE)]
            parts.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" fill="{color}" />')
            parts.append(f'<text x="{lx + 18}" y="{ly}" font-size="11" fill="{theme["text"]}">{_escape(name)}</text>')
            lx += 18 + 8 * len(str(name)) + 18
    parts.append("</svg>")
    return "".join(parts)


def _svg_line(labels, data, series_names, theme) -> str:
    W, H = 700, 320
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 50
    n = len(labels)
    flat = [float(v) for series in data for v in series]
    vmax = max(flat) if flat else 1.0
    vmin = min(flat) if flat else 0.0
    span = vmax - vmin if vmax != vmin else 1.0
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b
    step = chart_w / max(n - 1, 1)
    ticks = _nice_ticks(vmin, vmax, 5)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">']
    parts.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{H - pad_b}" stroke="{theme["border"]}" />')
    parts.append(f'<line x1="{pad_l}" y1="{H - pad_b}" x2="{W - pad_r}" y2="{H - pad_b}" stroke="{theme["border"]}" />')
    for t in ticks:
        y = (H - pad_b) - ((t - vmin) / span) * chart_h
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - pad_r}" y2="{y:.1f}" stroke="{theme["border"]}" stroke-dasharray="2,3" opacity="0.6" />')
        parts.append(f'<text x="{pad_l - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{theme["muted"]}">{_fmt_num(t)}</text>')
    for si, series in enumerate(data):
        color = _CHART_PALETTE[si % len(_CHART_PALETTE)]
        pts = []
        for i in range(n):
            v = float(series[i]) if i < len(series) else 0.0
            x = pad_l + i * step
            y = (H - pad_b) - ((v - vmin) / span) * chart_h
            pts.append(f"{x:.1f},{y:.1f}")
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.4" />')
        for pt in pts:
            x, y = pt.split(",")
            parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{color}" />')
    for i, label in enumerate(labels):
        x = pad_l + i * step
        parts.append(f'<text x="{x:.1f}" y="{H - pad_b + 18}" text-anchor="middle" font-size="11" fill="{theme["text"]}">{_escape(str(label))}</text>')
    if len(data) > 1:
        lx, ly = pad_l, H - 12
        for si, name in enumerate(series_names):
            color = _CHART_PALETTE[si % len(_CHART_PALETTE)]
            parts.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" fill="{color}" />')
            parts.append(f'<text x="{lx + 18}" y="{ly}" font-size="11" fill="{theme["text"]}">{_escape(name)}</text>')
            lx += 18 + 8 * len(str(name)) + 18
    parts.append("</svg>")
    return "".join(parts)


def _svg_pie(labels, values, theme) -> str:
    import math
    W, H = 460, 320
    cx, cy, r = 160, H / 2, 130
    values = [max(float(v), 0.0) for v in values]
    total = sum(values) or 1.0
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">']
    a0 = -math.pi / 2
    for i, v in enumerate(values):
        frac = v / total
        a1 = a0 + frac * 2 * math.pi
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        large = 1 if (a1 - a0) > math.pi else 0
        color = _CHART_PALETTE[i % len(_CHART_PALETTE)]
        if len(values) == 1:
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" />')
        else:
            parts.append(
                f'<path d="M{cx:.1f},{cy:.1f} L{x0:.1f},{y0:.1f} '
                f'A{r:.1f},{r:.1f} 0 {large} 1 {x1:.1f},{y1:.1f} Z" '
                f'fill="{color}" stroke="#fff" stroke-width="1.5" />'
            )
        a0 = a1
    # Legend
    ly = 40
    for i, label in enumerate(labels[: len(values)]):
        v = values[i]
        pct = (v / total) * 100
        color = _CHART_PALETTE[i % len(_CHART_PALETTE)]
        parts.append(f'<rect x="320" y="{ly - 10}" width="12" height="12" fill="{color}" />')
        parts.append(f'<text x="340" y="{ly}" font-size="12" fill="{theme["text"]}">{_escape(label)} — {pct:.1f}%</text>')
        ly += 22
    parts.append("</svg>")
    return "".join(parts)


def _nice_ticks(vmin: float, vmax: float, n: int) -> List[float]:
    import math
    if vmax == vmin:
        vmax = vmin + 1
    span = vmax - vmin
    raw = span / max(n, 1)
    mag = 10 ** math.floor(math.log10(raw))
    norm = raw / mag
    if norm < 1.5:
        step = 1 * mag
    elif norm < 3:
        step = 2 * mag
    elif norm < 7:
        step = 5 * mag
    else:
        step = 10 * mag
    start = math.floor(vmin / step) * step
    end = math.ceil(vmax / step) * step
    ticks: List[float] = []
    v = start
    while v <= end + 1e-9:
        ticks.append(round(v, 6))
        v += step
    return ticks


def _fmt_num(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.1f}k"
    if abs(v - int(v)) < 1e-6:
        return f"{int(v)}"
    return f"{v:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# Misc renderers
# ---------------------------------------------------------------------------


def _r_timeline(el: dict, theme) -> str:
    items = el.get("items") or []
    lis: List[str] = []
    for it in items:
        when = it.get("when") or ""
        title = it.get("title") or ""
        text = it.get("text") or ""
        body_parts: List[str] = []
        if when:
            body_parts.append(f'<span class="when">{_inline(when)}</span>')
        if title:
            body_parts.append(f'<span class="title">{_inline(title)}</span>')
        if text:
            body_parts.append(f'<div>{_inline(text)}</div>')
        lis.append(f"<li>{''.join(body_parts)}</li>")
    return f'<ul class="timeline">{"".join(lis)}</ul>'


def _r_hrule(el: dict, theme) -> str:
    return '<hr class="rule">'


def _r_spacer(el: dict, theme) -> str:
    h = float(el.get("height") or 12)
    return f'<div class="spacer" style="height:{h}px;"></div>'


def _r_image(el: dict, theme) -> str:
    path = el.get("path")
    alt = el.get("alt") or ""
    if not path:
        raise ValueError("image requires `path`")
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"image not found: {path!r}")
    if not alt:
        raise ValueError(
            "image requires `alt` (accessible alternative text). "
            "Pass alt='decorative' for purely decorative imagery."
        )
    mime, _ = mimetypes.guess_type(p.name)
    mime = mime or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    width = el.get("width")
    width_attr = f' width="{int(width)}"' if width else ""
    caption = el.get("caption")
    img = f'<img class="embed" src="data:{mime};base64,{b64}" alt="{_attr("" if alt == "decorative" else alt)}"{width_attr}>'
    if caption:
        return f'<figure class="image">{img}<figcaption>{_inline(caption)}</figcaption></figure>'
    return img


def _r_raw_html(el: dict, theme) -> str:
    # Escape-hatch for advanced authors. The skill warns against using it
    # for untrusted content.
    return str(el.get("html") or "")


def _r_page_break(el: dict, theme) -> str:
    return '<div class="page-break" aria-hidden="true"></div>'


def _r_toc(el: dict, theme) -> str:
    items = el.get("items") or []
    title = el.get("title") or "Contents"
    if not items:
        return ""
    lis: List[str] = []
    for it in items:
        if isinstance(it, str):
            text, href = it, ""
        else:
            text = it.get("text") or ""
            href = it.get("href") or ""
        if href and not href.startswith("#"):
            href = f"#{href}"
        if href:
            lis.append(f'<li><a href="{_attr(href)}">{_inline(text)}</a></li>')
        else:
            lis.append(f"<li>{_inline(text)}</li>")
    return f'<nav class="toc" aria-label="Table of contents"><h2>{_inline(title)}</h2><ol>{"".join(lis)}</ol></nav>'


def _r_details(el: dict, theme) -> str:
    summary = el.get("summary") or "Details"
    text = el.get("text")
    children = el.get("children") or []
    parts: List[str] = [f"<summary>{_inline(summary)}</summary>"]
    if text:
        parts.append(f"<p>{_inline(text)}</p>")
    for child in children:
        if not isinstance(child, dict):
            continue
        kind = child.get("type")
        fn = _RENDERERS.get(kind)
        if fn:
            parts.append(fn(child, theme))
    open_attr = " open" if el.get("open") else ""
    return f'<details class="collapsible"{open_attr}>{"".join(parts)}</details>'


_RENDERERS = {
    "cover": _r_cover,
    "title": _r_title,
    "heading": _r_heading,
    "paragraph": _r_paragraph,
    "bullets": _r_bullets,
    "numbered": _r_numbered,
    "callout": _r_callout,
    "quote": _r_quote,
    "banner": _r_banner,
    "kpi_row": _r_kpi_row,
    "card": _r_card,
    "columns": _r_columns,
    "badges": _r_badges,
    "table": _r_table,
    "chart": _r_chart,
    "timeline": _r_timeline,
    "hrule": _r_hrule,
    "spacer": _r_spacer,
    "image": _r_image,
    "raw_html": _r_raw_html,
    "page_break": _r_page_break,
    "toc": _r_toc,
    "details": _r_details,
}
