"""
Tests for the `html` tool domain.

Most tests are pure-Python (no `soffice` or `pypdfium2` required). The
`to_pdf` and `see` tests are gated on the presence of `soffice` on PATH;
if it's absent, they exercise the `dependency_missing` path instead.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from runtime import tool_registry
from runtime.tool_registry import ToolCtx


def _ctx() -> ToolCtx:
    return ToolCtx(
        run_id="t",
        user_id="u",
        pack_name="p",
        classification_ceiling="internal",
        allowed_data_sources=[],
    )


def _make_html(path: Path, *, with_external=False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    extras = (
        '<link rel="stylesheet" href="https://cdn.example.com/x.css">' if with_external else ""
    )
    path.write_text(f"""<!doctype html>
<html><head><title>Hi there</title>{extras}<style>p {{ color: red; }}</style></head>
<body>
<h1>Hello</h1>
<p>First paragraph.</p>
<p>Second paragraph with <a href="https://example.com">a link</a>.</p>
<table><tr><th>A</th></tr><tr><td>1</td></tr></table>
<img src="data:image/png;base64,AAAA" alt="tiny pixel">
<script>console.log('ignored');</script>
</body></html>""", encoding="utf-8")


# ---------------------------------------------------------------------------
# html.read
# ---------------------------------------------------------------------------


def test_read_happy(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.html"
    _make_html(p)
    r = tool_registry.call("html.read", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert r.data["title"] == "Hi there"
    assert r.data["self_contained"] is True
    assert r.data["counts"]["headings"] == 1
    assert r.data["counts"]["paragraphs"] == 2
    assert r.data["counts"]["tables"] == 1
    assert r.data["counts"]["images"] == 1
    assert r.data["counts"]["scripts"] == 1
    assert r.data["counts"]["styles"] == 1


def test_read_detects_external(tmp_path):
    tool_registry.discover()
    p = tmp_path / "ext.html"
    _make_html(p, with_external=True)
    r = tool_registry.call("html.read", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert r.data["self_contained"] is False


def test_read_file_not_found():
    tool_registry.discover()
    r = tool_registry.call("html.read", {"path": "/tmp/nope-xyz.html"}, _ctx())
    assert not r.ok
    assert r.error.code == "file_not_found"


def test_read_unsupported_extension(tmp_path):
    tool_registry.discover()
    p = tmp_path / "foo.txt"
    p.write_text("nope")
    r = tool_registry.call("html.read", {"path": str(p)}, _ctx())
    assert not r.ok
    assert r.error.code == "unsupported_format"


# ---------------------------------------------------------------------------
# html.extract_text
# ---------------------------------------------------------------------------


def test_extract_text_basic(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.html"
    _make_html(p)
    r = tool_registry.call("html.extract_text", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert "Hello" in r.data["text"]
    assert "First paragraph" in r.data["text"]
    assert "ignored" not in r.data["text"]  # <script> stripped
    assert "[image: tiny pixel]" in r.data["text"]
    assert r.data["title"] == "Hi there"


def test_extract_text_truncation(tmp_path):
    tool_registry.discover()
    p = tmp_path / "long.html"
    body = "<p>" + ("word " * 1000) + "</p>"
    p.write_text(f"<!doctype html><html><body>{body}</body></html>", encoding="utf-8")
    r = tool_registry.call(
        "html.extract_text",
        {"path": str(p), "max_chars": 200},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["truncated"] is True
    assert r.data["char_count"] == 200


# ---------------------------------------------------------------------------
# html.create
# ---------------------------------------------------------------------------


def test_create_minimal(tmp_path):
    tool_registry.discover()
    out = tmp_path / "min.html"
    r = tool_registry.call(
        "html.create",
        {
            "output": str(out),
            "title": "Minimal",
            "elements": [{"type": "title", "text": "Hello world"}],
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert "<title>Minimal</title>" in body
    assert "Hello world" in body
    assert "<style>" in body  # inline CSS
    assert "@media print" in body
    assert "http://" not in body  # no external URLs
    assert r.data["self_contained"] is True


def test_create_full_report(tmp_path):
    tool_registry.discover()
    out = tmp_path / "full.html"
    r = tool_registry.call(
        "html.create",
        {
            "output": str(out),
            "title": "Weekly Status",
            "theme": "professional",
            "header": {"left": "Project", "right": "Week 21"},
            "footer": "Confidential",
            "elements": [
                {"type": "cover", "title": "Weekly Status",
                 "subtitle": "Project Lighthouse",
                 "tagline": "Internal"},
                {"type": "toc", "items": [
                    {"text": "Numbers", "href": "n"},
                    {"text": "What shipped", "href": "s"},
                ]},
                {"type": "heading", "level": 2, "id": "n", "text": "Numbers"},
                {"type": "kpi_row", "items": [
                    {"label": "Users", "value": "1.2M", "delta": "+8%", "direction": "up"},
                    {"label": "Latency", "value": "180ms"},
                ]},
                {"type": "chart", "kind": "bar", "title": "Quarterly",
                 "labels": ["Q1", "Q2", "Q3"], "data": [[10, 20, 30]],
                 "series_names": ["Rev"]},
                {"type": "chart", "kind": "line", "title": "Trend",
                 "labels": ["M","T","W"], "data": [[5,6,7]]},
                {"type": "chart", "kind": "pie", "title": "Share",
                 "labels": ["A","B","C"], "data": [[40,35,25]]},
                {"type": "heading", "level": 2, "id": "s", "text": "Shipped"},
                {"type": "bullets", "items": ["A", "B with <b>bold</b>", "C"]},
                {"type": "numbered", "items": ["one", "two"]},
                {"type": "callout", "variant": "warning",
                 "title": "Watch out", "text": "Vendor delay."},
                {"type": "callout", "variant": "success", "text": "Sales up."},
                {"type": "quote", "text": "Be bold.", "attribution": "Anon"},
                {"type": "banner", "text": "Important", "subtitle": "Sub"},
                {"type": "table", "header": True, "caption": "Top 3",
                 "rows": [["#", "Account", "ARR"],
                          ["1", "Acme", "$1.4M"],
                          ["2", "Globex", "$1.1M"]]},
                {"type": "columns", "columns": [
                    [{"type": "paragraph", "text": "Left column."}],
                    [{"type": "paragraph", "text": "Right column."}],
                ]},
                {"type": "badges", "items": ["draft", {"text": "urgent", "color": "#dc2626"}]},
                {"type": "timeline", "items": [
                    {"when": "Mon", "title": "Kickoff"},
                    {"when": "Wed", "title": "Review"},
                ]},
                {"type": "details", "summary": "Methodology",
                 "text": "We computed X by Y."},
                {"type": "card", "title": "A card",
                 "children": [{"type": "paragraph", "text": "Inside."}]},
                {"type": "hrule"},
                {"type": "spacer", "height": 20},
                {"type": "page_break"},
                {"type": "paragraph", "text": "Next page in print."},
            ],
        },
        _ctx(),
    )
    assert r.ok, r.error
    body = out.read_text(encoding="utf-8")
    # SVG charts present and inline
    assert body.count("<svg") >= 3
    # TOC anchors match
    assert 'id="n"' in body and 'id="s"' in body
    assert 'href="#n"' in body and 'href="#s"' in body
    # Inline markup preserved in bullets
    assert "<b>bold</b>" in body
    # No external resource references
    assert "https://" not in body or 'href="https://' not in body  # links are fine
    assert r.data["element_count"] >= 20


def test_create_with_image(tmp_path):
    tool_registry.discover()
    # Make a tiny PNG via raw bytes (1x1 transparent)
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
    )
    img = tmp_path / "p.png"
    img.write_bytes(png)
    out = tmp_path / "with-image.html"
    r = tool_registry.call(
        "html.create",
        {
            "output": str(out),
            "elements": [
                {"type": "image", "path": str(img), "alt": "tiny pixel",
                 "caption": "Pixel"},
            ],
        },
        _ctx(),
    )
    assert r.ok, r.error
    body = out.read_text(encoding="utf-8")
    assert "data:image/png;base64," in body
    assert 'alt="tiny pixel"' in body


def test_create_image_requires_alt(tmp_path):
    tool_registry.discover()
    img = tmp_path / "p.png"
    img.write_bytes(b"x")
    out = tmp_path / "x.html"
    r = tool_registry.call(
        "html.create",
        {
            "output": str(out),
            "elements": [{"type": "image", "path": str(img)}],
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "create_failed"
    assert "alt" in r.error.message.lower()


def test_create_unknown_element_type(tmp_path):
    tool_registry.discover()
    out = tmp_path / "x.html"
    r = tool_registry.call(
        "html.create",
        {"output": str(out), "elements": [{"type": "no_such_type"}]},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "create_failed"


def test_create_empty_elements(tmp_path):
    tool_registry.discover()
    out = tmp_path / "x.html"
    r = tool_registry.call(
        "html.create",
        {"output": str(out), "elements": []},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_create_output_exists_no_overwrite(tmp_path):
    tool_registry.discover()
    out = tmp_path / "x.html"
    out.write_text("existing")
    r = tool_registry.call(
        "html.create",
        {"output": str(out), "elements": [{"type": "title", "text": "hi"}]},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "output_exists"


def test_create_overwrite(tmp_path):
    tool_registry.discover()
    out = tmp_path / "x.html"
    out.write_text("existing")
    r = tool_registry.call(
        "html.create",
        {
            "output": str(out),
            "overwrite": True,
            "elements": [{"type": "title", "text": "fresh"}],
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert "fresh" in out.read_text(encoding="utf-8")


def test_create_custom_theme(tmp_path):
    tool_registry.discover()
    out = tmp_path / "c.html"
    r = tool_registry.call(
        "html.create",
        {
            "output": str(out),
            "theme": {"primary": "ff0000", "background": "ffffff"},
            "elements": [{"type": "heading", "text": "Red"}],
        },
        _ctx(),
    )
    assert r.ok, r.error
    body = out.read_text(encoding="utf-8")
    assert "#ff0000" in body
    assert r.data["theme"] == "custom"


def test_create_escapes_script_injection(tmp_path):
    tool_registry.discover()
    out = tmp_path / "safe.html"
    r = tool_registry.call(
        "html.create",
        {
            "output": str(out),
            "elements": [
                {"type": "paragraph",
                 "text": "<script>alert('xss')</script> and a <b>bold</b> bit"},
            ],
        },
        _ctx(),
    )
    assert r.ok, r.error
    body = out.read_text(encoding="utf-8")
    assert "<script>alert" not in body
    assert "&lt;script&gt;alert" in body
    # But allowed inline tags ARE rendered
    assert "<b>bold</b>" in body


# ---------------------------------------------------------------------------
# html.to_pdf / html.see — depend on soffice
# ---------------------------------------------------------------------------


def _soffice_is_usable() -> bool:
    """True only if `soffice --version` actually launches. Catches the
    macOS broken-symlink / quarantined-app case where the wrapper
    script exists but the .app bundle does not."""
    bin_ = shutil.which("soffice") or shutil.which("libreoffice")
    if not bin_:
        return False
    import subprocess
    try:
        proc = subprocess.run([bin_, "--version"], capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


_HAS_SOFFICE = _soffice_is_usable()


@pytest.mark.skipif(_HAS_SOFFICE, reason="soffice present; test the absence path elsewhere.")
def test_to_pdf_dependency_missing(tmp_path):
    tool_registry.discover()
    p = tmp_path / "x.html"
    _make_html(p)
    out = tmp_path / "x.pdf"
    r = tool_registry.call("html.to_pdf", {"path": str(p), "output": str(out)}, _ctx())
    assert not r.ok
    assert r.error.code == "dependency_missing"


@pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not on PATH")
def test_to_pdf_smoke(tmp_path):
    tool_registry.discover()
    p = tmp_path / "x.html"
    _make_html(p)
    out = tmp_path / "x.pdf"
    r = tool_registry.call(
        "html.to_pdf",
        {"path": str(p), "output": str(out), "timeout_seconds": 180},
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    assert r.data["size_bytes"] > 100


@pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not on PATH")
def test_see_smoke(tmp_path):
    tool_registry.discover()
    p = tmp_path / "x.html"
    _make_html(p)
    r = tool_registry.call(
        "html.see",
        {"path": str(p), "timeout_seconds": 180},
        _ctx(),
    )
    assert r.ok, r.error
    assert len(r.images) == 1
    assert r.images[0].mime == "image/png"


@pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not on PATH")
def test_see_too_many_pages(tmp_path):
    tool_registry.discover()
    # Build a deliberately long doc by stuffing it with many paragraphs so it
    # paginates to well over 5 pages once LibreOffice imposes A4 size.
    out = tmp_path / "long.html"
    paras = "\n".join(f"<p>Line {i}: " + ("lorem ipsum " * 20) + "</p>" for i in range(400))
    out.write_text(
        f"<!doctype html><html><body>{paras}</body></html>",
        encoding="utf-8",
    )
    r = tool_registry.call(
        "html.see",
        {"path": str(out), "pages": "1-6", "timeout_seconds": 180},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "too_many_pages"
