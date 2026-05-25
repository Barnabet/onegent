"""
Tests for the `pptx` tool domain.

Builds small `.pptx` files at runtime via python-pptx so there's no fixture
dependency. Heavier behaviours (`convert`, `see` — both LibreOffice-backed)
are gated on `soffice` being available; if it isn't, those tests just
assert the `dependency_missing` error path.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from runtime import tool_registry
from runtime.tool_registry import ToolCtx


pytest.importorskip("pptx")


def _ctx() -> ToolCtx:
    return ToolCtx(
        run_id="t",
        user_id="u",
        pack_name="p",
        classification_ceiling="internal",
        allowed_data_sources=[],
    )


def _make_pptx(path: Path, slides: int = 2, *, with_notes: bool = False, title_prefix: str = "Slide") -> None:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    layout = prs.slide_layouts[5]  # "Title Only"
    for i in range(slides):
        slide = prs.slides.add_slide(layout)
        if slide.shapes.title is not None:
            slide.shapes.title.text = f"{title_prefix} {i+1}"
        # A body textbox so extract_text has something to find.
        box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1))
        box.text_frame.text = f"Body of slide {i+1}"
        if with_notes:
            slide.notes_slide.notes_text_frame.text = f"Notes for slide {i+1}"

    prs.core_properties.title = "Test Deck"
    prs.core_properties.author = "pytest"
    path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(path))


# ---------------------------------------------------------------------------
# pptx.read
# ---------------------------------------------------------------------------


def test_read_happy(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=3, with_notes=True)
    r = tool_registry.call("pptx.read", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert r.data["slide_count"] == 3
    assert r.data["metadata"]["title"] == "Test Deck"
    assert len(r.data["slides"]) == 3
    assert r.data["slides"][0]["title"] == "Slide 1"
    assert r.data["slides"][0]["has_notes"] is True


def test_read_file_not_found():
    tool_registry.discover()
    r = tool_registry.call("pptx.read", {"path": "/tmp/nope-xyz-123.pptx"}, _ctx())
    assert not r.ok
    assert r.error.code == "file_not_found"


def test_read_unsupported_extension(tmp_path):
    tool_registry.discover()
    p = tmp_path / "foo.docx"
    p.write_text("x")
    r = tool_registry.call("pptx.read", {"path": str(p)}, _ctx())
    assert not r.ok
    assert r.error.code == "unsupported_format"


# ---------------------------------------------------------------------------
# pptx.extract_text / extract_notes
# ---------------------------------------------------------------------------


def test_extract_text_full(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=3, with_notes=True)
    r = tool_registry.call("pptx.extract_text", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert r.data["slide_count"] == 3
    assert "Body of slide 1" in r.data["slides"][0]["text"]
    assert "Notes for slide 1" in r.data["slides"][0]["notes"]


def test_extract_text_subset(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=4)
    r = tool_registry.call(
        "pptx.extract_text",
        {"path": str(p), "slides": "2-3", "include_notes": False},
        _ctx(),
    )
    assert r.ok, r.error
    assert [s["slide"] for s in r.data["slides"]] == [2, 3]
    assert all(s["notes"] == "" for s in r.data["slides"])


def test_extract_text_bad_range(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=2)
    r = tool_registry.call("pptx.extract_text", {"path": str(p), "slides": "5"}, _ctx())
    assert not r.ok
    assert r.error.code == "slide_out_of_range"


def test_extract_notes(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=3, with_notes=True)
    r = tool_registry.call("pptx.extract_notes", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert r.data["slides_with_notes"] == 3
    assert r.data["slides"][1]["notes"].startswith("Notes for slide 2")


# ---------------------------------------------------------------------------
# pptx.merge / split
# ---------------------------------------------------------------------------


def test_merge_two_decks(tmp_path):
    tool_registry.discover()
    a = tmp_path / "a.pptx"
    b = tmp_path / "b.pptx"
    _make_pptx(a, slides=2, title_prefix="A")
    _make_pptx(b, slides=3, title_prefix="B")
    out = tmp_path / "merged.pptx"
    r = tool_registry.call(
        "pptx.merge",
        {"inputs": [str(a), str(b)], "output": str(out)},
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    # Read back and check count
    r2 = tool_registry.call("pptx.read", {"path": str(out)}, _ctx())
    assert r2.ok, r2.error
    assert r2.data["slide_count"] == 5


def test_merge_requires_two_inputs(tmp_path):
    tool_registry.discover()
    a = tmp_path / "a.pptx"
    _make_pptx(a, slides=1)
    out = tmp_path / "merged.pptx"
    r = tool_registry.call(
        "pptx.merge",
        {"inputs": [str(a)], "output": str(out)},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_split_keep_subset(tmp_path):
    tool_registry.discover()
    src = tmp_path / "doc.pptx"
    _make_pptx(src, slides=5)
    out = tmp_path / "subset.pptx"
    r = tool_registry.call(
        "pptx.split",
        {"path": str(src), "slides": "2-4", "output": str(out)},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["slide_count"] == 3
    r2 = tool_registry.call("pptx.read", {"path": str(out)}, _ctx())
    assert r2.ok, r2.error
    assert r2.data["slide_count"] == 3


def test_split_reorder(tmp_path):
    tool_registry.discover()
    src = tmp_path / "doc.pptx"
    _make_pptx(src, slides=3, title_prefix="X")
    out = tmp_path / "reordered.pptx"
    r = tool_registry.call(
        "pptx.split",
        {"path": str(src), "slides": "3,1,2", "output": str(out)},
        _ctx(),
    )
    assert r.ok, r.error
    r2 = tool_registry.call("pptx.read", {"path": str(out)}, _ctx())
    assert r2.ok, r2.error
    titles = [s["title"] for s in r2.data["slides"]]
    assert titles == ["X 3", "X 1", "X 2"]


# ---------------------------------------------------------------------------
# pptx.create
# ---------------------------------------------------------------------------


def test_create_basic_deck(tmp_path):
    tool_registry.discover()
    out = tmp_path / "out.pptx"
    r = tool_registry.call(
        "pptx.create",
        {
            "output": str(out),
            "theme": "professional",
            "page_numbers": True,
            "slides": [
                {"type": "cover", "title": "Title", "subtitle": "Sub", "tagline": "Tag"},
                {"type": "content", "title": "Bullets",
                 "bullets": ["A", "B", "C"]},
                {"type": "kpi", "title": "Numbers", "items": [
                    {"label": "Users", "value": "1.2M"},
                    {"label": "Revenue", "value": "$3.4M", "delta": "+12%"},
                    {"label": "Churn", "value": "2.1%"},
                ]},
                {"type": "table", "title": "Table",
                 "rows": [["A", "B"], ["1", "2"], ["3", "4"]]},
                {"type": "chart", "title": "Chart", "kind": "bar",
                 "labels": ["Q1", "Q2"], "data": [[10, 20]],
                 "series_names": ["Sales"]},
                {"type": "two_column", "title": "Two",
                 "left":  {"header": "L", "items": ["l1", "l2"]},
                 "right": {"header": "R", "items": ["r1"]}},
                {"type": "quote", "text": "Be bold.", "attribution": "Anon"},
                {"type": "conclusion", "title": "Done", "subtitle": "Thanks"},
            ],
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    assert r.data["slide_count"] == 8
    # Confirm it opens and has the right number of slides
    r2 = tool_registry.call("pptx.read", {"path": str(out)}, _ctx())
    assert r2.ok, r2.error
    assert r2.data["slide_count"] == 8


def test_create_unknown_slide_type(tmp_path):
    tool_registry.discover()
    out = tmp_path / "out.pptx"
    r = tool_registry.call(
        "pptx.create",
        {"output": str(out), "slides": [{"type": "no_such_type"}]},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "create_failed"


def test_create_empty_slides_invalid(tmp_path):
    tool_registry.discover()
    out = tmp_path / "out.pptx"
    r = tool_registry.call(
        "pptx.create",
        {"output": str(out), "slides": []},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_create_unknown_theme(tmp_path):
    tool_registry.discover()
    out = tmp_path / "out.pptx"
    r = tool_registry.call(
        "pptx.create",
        {
            "output": str(out),
            "theme": "nonsense",
            "slides": [{"type": "title", "text": "Hello"}],
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "create_failed"


# ---------------------------------------------------------------------------
# pptx.convert / pptx.see — only run end-to-end if soffice is available.
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


@pytest.mark.skipif(_HAS_SOFFICE, reason="soffice is present; test exercises the absence path.")
def test_convert_dependency_missing_when_no_soffice(tmp_path, monkeypatch):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=1)
    out = tmp_path / "out.pdf"
    r = tool_registry.call(
        "pptx.convert",
        {"path": str(p), "output": str(out)},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "dependency_missing"


@pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not on PATH")
def test_convert_to_pdf(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=2)
    out = tmp_path / "out.pdf"
    r = tool_registry.call(
        "pptx.convert",
        {"path": str(p), "output": str(out), "timeout_seconds": 180},
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    assert r.data["size_bytes"] > 100


@pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not on PATH")
def test_see_renders_first_slide(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=3)
    r = tool_registry.call(
        "pptx.see",
        {"path": str(p), "timeout_seconds": 180},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["slide_count"] == 3
    assert len(r.images) == 1
    assert r.images[0].mime == "image/png"


@pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not on PATH")
def test_see_too_many_slides(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pptx"
    _make_pptx(p, slides=8)
    r = tool_registry.call(
        "pptx.see",
        {"path": str(p), "slides": "1-6"},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "too_many_slides"


# ---------------------------------------------------------------------------
# pptx.from_html — render a complete HTML document to a picture-per-slide deck
# ---------------------------------------------------------------------------


def _from_html_renderer_available() -> bool:
    """True when both `pypdfium2` *and* a working HTML-to-PDF engine are
    importable. Gates the heavy end-to-end tests so a partial install
    just skips the slow path instead of failing the whole suite."""
    try:
        import pypdfium2  # noqa: F401
    except Exception:
        return False
    if _HAS_SOFFICE:
        return True
    try:
        from tools.pdf.create import _ensure_native_lib_path
        _ensure_native_lib_path()
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


_FROM_HTML_AVAILABLE = _from_html_renderer_available()


_SLIDE_DOC = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<style>"
    "@page { size: 13.333in 7.5in; margin: 0 }"
    "body { margin: 0; font-family: sans-serif; }"
    ".slide { width: 13.333in; height: 7.5in;"
    "         padding: 0.75in; box-sizing: border-box;"
    "         page-break-after: always; }"
    ".slide:last-child { page-break-after: auto; }"
    ".cover { background: #0f172a; color: white; }"
    "</style></head><body>"
    "<section class='slide cover'><h1>Cover</h1></section>"
    "<section class='slide'><h2>Body</h2><p>Some content.</p></section>"
    "</body></html>"
)


@pytest.mark.skipif(not _FROM_HTML_AVAILABLE, reason="no HTML→PDF renderer or pypdfium2 missing")
def test_from_html_minimal(tmp_path):
    tool_registry.discover()
    out = tmp_path / "deck.pptx"
    r = tool_registry.call(
        "pptx.from_html",
        {"output": str(out), "html": _SLIDE_DOC},
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    assert r.data["slide_count"] == 2
    assert r.data["image_format"] == "png"
    # 13.333in × 7.5in (16:9) was declared in the @page rule.
    assert abs(r.data["slide_width_in"] - 13.333) < 0.05
    assert abs(r.data["slide_height_in"] - 7.5) < 0.05

    # Re-open and confirm shape geometry: one Picture per slide,
    # full-bleed against the slide size.
    from pptx import Presentation
    prs = Presentation(str(out))
    assert len(prs.slides) == 2
    for s in prs.slides:
        pics = [sh for sh in s.shapes if sh.shape_type == 13]  # MSO_SHAPE_TYPE.PICTURE = 13
        assert len(pics) == 1
        pic = pics[0]
        assert pic.left == 0 and pic.top == 0
        assert pic.width == prs.slide_width
        assert pic.height == prs.slide_height


@pytest.mark.skipif(not _FROM_HTML_AVAILABLE, reason="no HTML→PDF renderer or pypdfium2 missing")
def test_from_html_speaker_notes(tmp_path):
    tool_registry.discover()
    out = tmp_path / "withnotes.pptx"
    r = tool_registry.call(
        "pptx.from_html",
        {
            "output": str(out),
            "html": _SLIDE_DOC,
            "notes": ["Cover narration.", "Body narration."],
        },
        _ctx(),
    )
    assert r.ok, r.error

    from pptx import Presentation
    prs = Presentation(str(out))
    assert prs.slides[0].notes_slide.notes_text_frame.text == "Cover narration."
    assert prs.slides[1].notes_slide.notes_text_frame.text == "Body narration."


@pytest.mark.skipif(not _FROM_HTML_AVAILABLE, reason="no HTML→PDF renderer or pypdfium2 missing")
def test_from_html_custom_aspect_ratio(tmp_path):
    """Slide dimensions come from the @page rule — not a fixed 16:9."""
    tool_registry.discover()
    out = tmp_path / "square.pptx"
    square_doc = (
        "<!doctype html><html><head>"
        "<style>@page { size: 1080px 1080px; margin: 0 }"
        "body { margin: 0; background: #0f172a; }</style>"
        "</head><body><div style='width:1080px;height:1080px'></div></body></html>"
    )
    r = tool_registry.call(
        "pptx.from_html",
        {"output": str(out), "html": square_doc},
        _ctx(),
    )
    assert r.ok, r.error
    # 1080 CSS px @ 96 dpi = 11.25 inches; expect a square.
    assert abs(r.data["slide_width_in"] - r.data["slide_height_in"]) < 0.05
    assert abs(r.data["slide_width_in"] - 11.25) < 0.05


@pytest.mark.skipif(not _FROM_HTML_AVAILABLE, reason="no HTML→PDF renderer or pypdfium2 missing")
def test_from_html_jpeg_format(tmp_path):
    tool_registry.discover()
    out = tmp_path / "jpeg.pptx"
    r = tool_registry.call(
        "pptx.from_html",
        {
            "output": str(out),
            "html": _SLIDE_DOC,
            "image_format": "jpeg",
            "jpeg_quality": 70,
            "image_dpi": 96,
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["image_format"] == "jpeg"
    assert r.data["image_dpi"] == 96


@pytest.mark.skipif(not _FROM_HTML_AVAILABLE, reason="no HTML→PDF renderer or pypdfium2 missing")
def test_from_html_accepts_file_path(tmp_path):
    tool_registry.discover()
    src = tmp_path / "src.html"
    src.write_text(_SLIDE_DOC, encoding="utf-8")
    out = tmp_path / "fromfile.pptx"
    r = tool_registry.call(
        "pptx.from_html",
        {"output": str(out), "html": str(src)},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["slide_count"] == 2


@pytest.mark.skipif(not _FROM_HTML_AVAILABLE, reason="no HTML→PDF renderer or pypdfium2 missing")
def test_from_html_sets_metadata(tmp_path):
    tool_registry.discover()
    out = tmp_path / "meta.pptx"
    r = tool_registry.call(
        "pptx.from_html",
        {
            "output": str(out),
            "html": _SLIDE_DOC,
            "title": "Deck Title",
            "author": "Author Name",
            "subject": "Deck Subject",
        },
        _ctx(),
    )
    assert r.ok, r.error
    from pptx import Presentation
    cp = Presentation(str(out)).core_properties
    assert cp.title == "Deck Title"
    assert cp.author == "Author Name"
    assert cp.subject == "Deck Subject"


def test_from_html_requires_pptx_extension(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pptx.from_html",
        {"output": str(tmp_path / "x.zip"), "html": _SLIDE_DOC},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_from_html_no_overwrite(tmp_path):
    tool_registry.discover()
    out = tmp_path / "x.pptx"
    out.write_bytes(b"stub")
    r = tool_registry.call(
        "pptx.from_html",
        {"output": str(out), "html": _SLIDE_DOC},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "output_exists"


def test_from_html_rejects_fragment(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pptx.from_html",
        {"output": str(tmp_path / "f.pptx"), "html": "<h1>just a fragment</h1>"},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_from_html_rejects_bad_dpi(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pptx.from_html",
        {
            "output": str(tmp_path / "d.pptx"),
            "html": _SLIDE_DOC,
            "image_dpi": 9999,
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_from_html_rejects_bad_image_format(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pptx.from_html",
        {
            "output": str(tmp_path / "d.pptx"),
            "html": _SLIDE_DOC,
            "image_format": "webp",
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


@pytest.mark.skipif(not _FROM_HTML_AVAILABLE, reason="no HTML→PDF renderer or pypdfium2 missing")
def test_from_html_rejects_too_many_notes(tmp_path):
    tool_registry.discover()
    out = tmp_path / "n.pptx"
    r = tool_registry.call(
        "pptx.from_html",
        {
            "output": str(out),
            "html": _SLIDE_DOC,
            "notes": ["a", "b", "c", "d"],  # doc only renders to 2 slides
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


# ---------------------------------------------------------------------------
# pptx.from_html_editable — HTML → fully editable PPTX via Playwright
# ---------------------------------------------------------------------------


def _editable_renderer_available() -> bool:
    """True when Playwright + a usable Chromium are available."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


_EDITABLE_AVAILABLE = _editable_renderer_available()


_EDITABLE_DOC = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<style>"
    "body { margin: 0; font-family: Arial, sans-serif; color: #0f172a; }"
    ".slide { width: 13.333in; height: 7.5in; padding: 0.75in;"
    "         box-sizing: border-box; position: relative; }"
    ".cover { background: #0f172a; color: white; }"
    ".cover h1 { font-size: 60pt; margin: 0; }"
    ".card { background: #f1f5f9; border-radius: 12px;"
    "        padding: 24px; width: 4in; }"
    ".card .v { font-size: 36pt; font-weight: 800; }"
    "table { border-collapse: collapse; width: 100%; }"
    "th { background: #0f172a; color: white; padding: 8px; }"
    "td { padding: 8px; border-bottom: 1px solid #ddd; }"
    "</style></head><body>"
    "<section class='slide cover'><h1>Editable Cover</h1></section>"
    "<section class='slide'>"
    "<h2>KPIs</h2>"
    "<div class='card'><div class='l'>Revenue</div><div class='v'>$4.2M</div></div>"
    "<table><tr><th>Cat</th><th>Val</th></tr>"
    "<tr><td>A</td><td>10</td></tr><tr><td>B</td><td>20</td></tr></table>"
    "</section></body></html>"
)


@pytest.mark.skipif(not _EDITABLE_AVAILABLE, reason="Playwright Chromium not available")
def test_from_html_editable_produces_native_shapes(tmp_path):
    tool_registry.discover()
    out = tmp_path / "editable.pptx"
    r = tool_registry.call(
        "pptx.from_html_editable",
        {"output": str(out), "html": _EDITABLE_DOC},
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    assert r.data["slide_count"] == 2
    assert r.data["editable"] is True
    assert abs(r.data["slide_width_in"] - 13.333) < 0.05

    # Re-open and confirm we got native text + tables, not pictures.
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    prs = Presentation(str(out))
    assert len(prs.slides) == 2

    # Cover slide: at least one text frame containing "Editable Cover".
    cover_texts = [
        sh.text_frame.text
        for sh in prs.slides[0].shapes
        if sh.has_text_frame
    ]
    assert any("Editable Cover" in t for t in cover_texts)

    # KPI slide: must contain a real table.
    kpi_shapes = list(prs.slides[1].shapes)
    assert any(sh.has_table for sh in kpi_shapes)
    table_shape = next(sh for sh in kpi_shapes if sh.has_table)
    assert table_shape.table.cell(0, 0).text_frame.text.strip() == "Cat"

    # No slide should be a single picture (that's the from_html mode).
    for s in prs.slides:
        pics = [sh for sh in s.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE]
        assert len(pics) == 0


def test_from_html_editable_requires_pptx_extension(tmp_path):
    tool_registry.discover()
    out = tmp_path / "deck.txt"
    r = tool_registry.call(
        "pptx.from_html_editable",
        {"output": str(out), "html": _EDITABLE_DOC},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_from_html_editable_rejects_empty_html(tmp_path):
    tool_registry.discover()
    out = tmp_path / "deck.pptx"
    r = tool_registry.call(
        "pptx.from_html_editable",
        {"output": str(out), "html": "   "},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


@pytest.mark.skipif(not _EDITABLE_AVAILABLE, reason="Playwright Chromium not available")
def test_from_html_editable_no_inline_text_duplication(tmp_path):
    """Regression: an inline tag inside a block (here <b>) must not
    emit its own text atom in addition to the block's. Previously a
    paragraph like `<p><b>Key:</b> value</p>` produced two text frames
    — one for the whole sentence and a second one over the bold prefix.
    """
    tool_registry.discover()
    out = tmp_path / "dup.pptx"
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{margin:0;font-family:Arial}"
        ".slide{width:13.333in;height:7.5in;padding:1in;box-sizing:border-box}"
        "</style></head><body>"
        "<section class='slide'>"
        "<p class='callout'><b>Key signal:</b> 149 SKUs are low stock.</p>"
        "</section></body></html>"
    )
    r = tool_registry.call(
        "pptx.from_html_editable",
        {"output": str(out), "html": html},
        _ctx(),
    )
    assert r.ok, r.error

    from pptx import Presentation

    prs = Presentation(str(out))
    slide = prs.slides[0]
    texts = [
        sh.text_frame.text.strip()
        for sh in slide.shapes
        if sh.has_text_frame and sh.text_frame.text.strip()
    ]
    # The bold prefix may only appear as part of the full sentence,
    # never as a standalone text frame.
    full = [t for t in texts if "149 SKUs are low stock" in t]
    bold_only = [t for t in texts if t == "Key signal:"]
    assert len(full) == 1, f"expected one full-sentence text frame, got {texts!r}"
    assert len(bold_only) == 0, f"bold prefix leaked as its own text frame: {texts!r}"
