"""
Tests for the `pdf` tool domain.

These tests build small PDFs at runtime (via pypdf) so they have no fixture
dependency. Heavier behaviours (OCR) are exercised through the
`dependency_missing` path so the suite stays cheap on machines without
tesseract installed.
"""

from __future__ import annotations

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


def _make_pdf(path: Path, pages: int = 2) -> None:
    """Build a tiny multi-page PDF using pypdf primitives."""
    pypdf = pytest.importorskip("pypdf")
    from pypdf import PdfWriter
    from pypdf.generic import RectangleObject

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "Test PDF", "/Author": "pytest"})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        writer.write(fh)
    # silence unused-import warning
    _ = RectangleObject


# ---------------------------------------------------------------------------
# pdf.read
# ---------------------------------------------------------------------------


def test_read_happy(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=3)
    r = tool_registry.call("pdf.read", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert r.data["page_count"] == 3
    assert r.data["encrypted"] is False
    assert r.data["metadata"]["title"] == "Test PDF"
    assert len(r.data["pages"]) == 3


def test_read_file_not_found():
    tool_registry.discover()
    r = tool_registry.call("pdf.read", {"path": "/tmp/nope-123.pdf"}, _ctx())
    assert not r.ok
    assert r.error.code == "file_not_found"


def test_read_unsupported_extension(tmp_path):
    tool_registry.discover()
    p = tmp_path / "foo.docx"
    p.write_text("x")
    r = tool_registry.call("pdf.read", {"path": str(p)}, _ctx())
    assert not r.ok
    assert r.error.code == "unsupported_format"


# ---------------------------------------------------------------------------
# pdf.extract_text — empty pages still parse cleanly
# ---------------------------------------------------------------------------


def test_extract_text_pages_spec(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=4)
    r = tool_registry.call(
        "pdf.extract_text",
        {"path": str(p), "pages": "1-2"},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["page_count"] == 2
    assert [pg["page"] for pg in r.data["pages"]] == [1, 2]


def test_extract_text_truncates_default_max_pages(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=8)

    # Default max_pages is 5 — should truncate.
    r = tool_registry.call("pdf.extract_text", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert r.data["page_count"] == 5            # pages actually returned
    assert [pg["page"] for pg in r.data["pages"]] == [1, 2, 3, 4, 5]
    assert r.data["truncated"] is True
    assert r.data["requested_page_count"] == 8
    assert r.data["returned_page_count"] == 5
    assert r.data["skipped_pages"] == [6, 7, 8]

    # Explicitly raising max_pages disables the cap.
    r2 = tool_registry.call(
        "pdf.extract_text", {"path": str(p), "max_pages": 20}, _ctx(),
    )
    assert r2.ok
    assert r2.data["page_count"] == 8
    assert r2.data.get("truncated") is None


def test_extract_text_page_out_of_range(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=2)
    r = tool_registry.call(
        "pdf.extract_text",
        {"path": str(p), "pages": "5"},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "page_out_of_range"


def test_extract_text_invalid_spec(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=2)
    r = tool_registry.call(
        "pdf.extract_text",
        {"path": str(p), "pages": "abc"},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


# ---------------------------------------------------------------------------
# pdf.merge / pdf.split / pdf.rotate
# ---------------------------------------------------------------------------


def test_merge_then_split(tmp_path):
    tool_registry.discover()
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _make_pdf(a, pages=2)
    _make_pdf(b, pages=3)
    merged = tmp_path / "merged.pdf"
    r = tool_registry.call(
        "pdf.merge",
        {"inputs": [str(a), str(b)], "output": str(merged)},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["page_count"] == 5

    # Now split out pages 2-4 of the merged file.
    sub = tmp_path / "sub.pdf"
    r2 = tool_registry.call(
        "pdf.split",
        {"path": str(merged), "pages": "2-4", "output": str(sub)},
        _ctx(),
    )
    assert r2.ok, r2.error
    assert r2.data["page_count"] == 3
    assert r2.data["selected_pages"] == [2, 3, 4]


def test_merge_too_few_inputs(tmp_path):
    tool_registry.discover()
    a = tmp_path / "a.pdf"
    _make_pdf(a)
    r = tool_registry.call(
        "pdf.merge",
        {"inputs": [str(a)], "output": str(tmp_path / "out.pdf")},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_merge_output_exists(tmp_path):
    tool_registry.discover()
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _make_pdf(a)
    _make_pdf(b)
    out = tmp_path / "out.pdf"
    out.write_text("preexisting")
    r = tool_registry.call(
        "pdf.merge",
        {"inputs": [str(a), str(b)], "output": str(out)},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "output_exists"


def test_rotate_invalid_degrees(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p)
    r = tool_registry.call(
        "pdf.rotate",
        {"path": str(p), "degrees": 45, "output": str(tmp_path / "r.pdf")},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_rotate_happy(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=2)
    out = tmp_path / "rot.pdf"
    r = tool_registry.call(
        "pdf.rotate",
        {"path": str(p), "degrees": 90, "pages": "1", "output": str(out)},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["rotated_pages"] == [1]


# ---------------------------------------------------------------------------
# pdf.encrypt / pdf.decrypt
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_roundtrip(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=1)
    enc = tmp_path / "enc.pdf"
    r = tool_registry.call(
        "pdf.encrypt",
        {"path": str(p), "user_password": "s3cret", "output": str(enc)},
        _ctx(),
    )
    assert r.ok, r.error

    # read it back without password — should report encrypted
    r2 = tool_registry.call("pdf.read", {"path": str(enc)}, _ctx())
    assert r2.ok
    assert r2.data["encrypted"] is True

    # wrong password
    r3 = tool_registry.call("pdf.read", {"path": str(enc), "password": "wrong"}, _ctx())
    assert not r3.ok
    assert r3.error.code == "password_required"

    # correct password
    r4 = tool_registry.call("pdf.read", {"path": str(enc), "password": "s3cret"}, _ctx())
    assert r4.ok
    assert r4.data["encrypted"] is False

    # decrypt to a new file
    dec = tmp_path / "dec.pdf"
    r5 = tool_registry.call(
        "pdf.decrypt",
        {"path": str(enc), "password": "s3cret", "output": str(dec)},
        _ctx(),
    )
    assert r5.ok, r5.error
    r6 = tool_registry.call("pdf.read", {"path": str(dec)}, _ctx())
    assert r6.ok and r6.data["encrypted"] is False


# ---------------------------------------------------------------------------
# pdf.form_fields / pdf.fill_form
# ---------------------------------------------------------------------------


def test_fill_form_no_fields(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p)
    out = tmp_path / "filled.pdf"
    r = tool_registry.call(
        "pdf.fill_form",
        {"path": str(p), "values": {"Name": "x"}, "output": str(out)},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "no_form_fields"


def test_form_fields_empty(tmp_path):
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p)
    r = tool_registry.call("pdf.form_fields", {"path": str(p)}, _ctx())
    assert r.ok
    assert r.data["fillable"] is False
    assert r.data["field_count"] == 0


# ---------------------------------------------------------------------------
# pdf.see
# ---------------------------------------------------------------------------


def test_see_renders_pages(tmp_path):
    pytest.importorskip("pypdfium2")
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=3)
    r = tool_registry.call(
        "pdf.see",
        {"path": str(p), "pages": "1-2"},
        _ctx(),
    )
    assert r.ok, r.error
    assert len(r.images) == 2
    assert all(img.mime == "image/png" for img in r.images)
    assert all(img.b64 for img in r.images)


def test_see_too_many_pages(tmp_path):
    pytest.importorskip("pypdfium2")
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=10)
    r = tool_registry.call(
        "pdf.see",
        {"path": str(p), "pages": "1-7"},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "too_many_pages"


def test_see_default_first_page(tmp_path):
    pytest.importorskip("pypdfium2")
    tool_registry.discover()
    p = tmp_path / "doc.pdf"
    _make_pdf(p, pages=4)
    r = tool_registry.call("pdf.see", {"path": str(p)}, _ctx())
    assert r.ok, r.error
    assert len(r.images) == 1
    assert r.data["rendered"][0]["page"] == 1


# ---------------------------------------------------------------------------
# pdf.create — render a complete HTML document to PDF via WeasyPrint
# (LibreOffice as a fallback). Tests that need a real PDF renderer are
# skipped when neither backend is available.
# ---------------------------------------------------------------------------


def _has_renderer() -> bool:
    """True when at least one of WeasyPrint or LibreOffice is usable."""
    import shutil
    import subprocess
    # Try LibreOffice — but only if `soffice --version` actually runs
    # (catches the macOS broken-symlink / quarantined-app case).
    bin_ = shutil.which("soffice") or shutil.which("libreoffice")
    if bin_:
        try:
            if subprocess.run([bin_, "--version"], capture_output=True, timeout=10).returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
    # Try WeasyPrint via the same helper that pdf.create uses, so the
    # native-lib auto-discovery has already run.
    try:
        from tools.pdf.create import _ensure_native_lib_path
        _ensure_native_lib_path()
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


_RENDERER_AVAILABLE = _has_renderer()


_MIN_DOC = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<title>T</title><style>@page{size:A4;margin:18mm}</style>"
    "</head><body><h1>Hi</h1></body></html>"
)


@pytest.mark.skipif(not _RENDERER_AVAILABLE, reason="no PDF renderer available")
def test_create_minimal_html_string(tmp_path):
    tool_registry.discover()
    out = tmp_path / "out.pdf"
    r = tool_registry.call(
        "pdf.create",
        {"output": str(out), "html": _MIN_DOC},
        _ctx(),
    )
    assert r.ok, r.error
    assert out.is_file()
    assert r.data["page_count"] >= 1
    assert r.data["size_bytes"] > 100
    assert r.data["engine"] in {"weasyprint", "libreoffice"}
    assert out.read_bytes()[:4] == b"%PDF"


@pytest.mark.skipif(not _RENDERER_AVAILABLE, reason="no PDF renderer available")
def test_create_from_html_file_path(tmp_path):
    """`html=` accepts an absolute path to a .html file on disk."""
    tool_registry.discover()
    src = tmp_path / "source.html"
    src.write_text(
        "<!doctype html><html><head><title>From file</title>"
        "<style>@page{size:letter;margin:0.75in}</style></head>"
        "<body><h1>Hello</h1><p>From a file.</p></body></html>",
        encoding="utf-8",
    )
    out = tmp_path / "frompath.pdf"
    r = tool_registry.call(
        "pdf.create",
        {"output": str(out), "html": str(src)},
        _ctx(),
    )
    assert r.ok, r.error
    assert out.read_bytes()[:4] == b"%PDF"


@pytest.mark.skipif(not _RENDERER_AVAILABLE, reason="no PDF renderer available")
def test_create_respects_custom_page_geometry(tmp_path):
    """The agent's own @page rule must win — we don't override it."""
    tool_registry.discover()
    out = tmp_path / "wide.pdf"
    # Landscape A4 with no margin: page width must come back as ~842pt
    # (A4 long side) not the WeasyPrint default of letter portrait.
    r = tool_registry.call(
        "pdf.create",
        {
            "output": str(out),
            "html": (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<style>@page{size:A4 landscape;margin:0}"
                "body{margin:0;background:#000;color:#fff;"
                "width:297mm;height:210mm}</style></head>"
                "<body><h1>Wide</h1></body></html>"
            ),
        },
        _ctx(),
    )
    assert r.ok, r.error

    # Only WeasyPrint reliably honours @page size; LibreOffice may not.
    if r.data["engine"] != "weasyprint":
        pytest.skip("page-size check only meaningful on WeasyPrint")

    from pypdf import PdfReader
    page = PdfReader(str(out)).pages[0]
    box = page.mediabox
    width = float(box.width)
    height = float(box.height)
    # A4 landscape: 842 x 595 pt. Allow a 2pt slop.
    assert width > height, f"expected landscape, got {width}x{height}"
    assert abs(width - 842.0) < 3, f"expected ~842pt width, got {width}"
    assert abs(height - 595.0) < 3, f"expected ~595pt height, got {height}"


@pytest.mark.skipif(not _RENDERER_AVAILABLE, reason="no PDF renderer available")
def test_create_sets_pdf_metadata(tmp_path):
    tool_registry.discover()
    out = tmp_path / "meta.pdf"
    r = tool_registry.call(
        "pdf.create",
        {
            "output": str(out),
            "html": _MIN_DOC,
            "title": "Custom Title",
            "author": "Test Author",
            "subject": "Test Subject",
        },
        _ctx(),
    )
    assert r.ok, r.error
    if r.data["engine"] != "weasyprint":
        pytest.skip("metadata kwargs are WeasyPrint-specific")

    from pypdf import PdfReader
    meta = PdfReader(str(out)).metadata or {}
    assert meta.get("/Title") == "Custom Title"
    assert meta.get("/Author") == "Test Author"
    assert meta.get("/Subject") == "Test Subject"


def test_create_requires_pdf_extension(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pdf.create",
        {"output": str(tmp_path / "out.txt"), "html": _MIN_DOC},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_create_no_overwrite(tmp_path):
    tool_registry.discover()
    out = tmp_path / "out.pdf"
    out.write_bytes(b"%PDF-1.4 stub")
    r = tool_registry.call(
        "pdf.create",
        {"output": str(out), "html": _MIN_DOC},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "output_exists"


def test_create_requires_html(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pdf.create",
        {"output": str(tmp_path / "a.pdf")},
        _ctx(),
    )
    # Pydantic-level rejection (missing required field) is also fine —
    # in either case the tool layer reports invalid_input.
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_create_rejects_html_fragment(tmp_path):
    """Fragments are rejected so the agent's @page rule has a chance."""
    tool_registry.discover()
    r = tool_registry.call(
        "pdf.create",
        {
            "output": str(tmp_path / "frag.pdf"),
            "html": "<h1>Hi</h1><p>Just a fragment.</p>",
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_create_rejects_missing_html_file(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pdf.create",
        {
            "output": str(tmp_path / "x.pdf"),
            "html": str(tmp_path / "does-not-exist.html"),
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_input"


def test_create_unknown_engine(tmp_path):
    tool_registry.discover()
    r = tool_registry.call(
        "pdf.create",
        {
            "output": str(tmp_path / "x.pdf"),
            "html": _MIN_DOC,
            "engine": "ghostscript",
        },
        _ctx(),
    )
    assert not r.ok and r.error.code == "invalid_input"
