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
