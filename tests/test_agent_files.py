"""
Tests for the agent-produced files plumbing:

  - subagent extracts output paths from tool results,
  - runs layer materialises file_created events into real conversation
    files via files_store.register_existing,
  - GET /api/files/{id}/download serves the bytes back.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Fresh conversations + uploads dirs and a fresh in-memory file store."""
    monkeypatch.setenv("CONVERSATIONS_DIR", str(tmp_path / "conversations"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    import server.conversations
    import server.files
    importlib.reload(server.conversations)
    importlib.reload(server.files)


def test_extract_output_paths_handles_known_shapes():
    from orchestrator.subagent import _extract_output_paths

    assert _extract_output_paths({"output": "/tmp/a.pdf"}) == ["/tmp/a.pdf"]
    assert _extract_output_paths({"outputs": ["/tmp/a.csv", "/tmp/b.csv"]}) == [
        "/tmp/a.csv", "/tmp/b.csv",
    ]
    # Single + many combine.
    assert _extract_output_paths(
        {"output": "/tmp/a.pdf", "outputs": ["/tmp/b.pdf"]}
    ) == ["/tmp/a.pdf", "/tmp/b.pdf"]
    # Empty / non-string entries are dropped.
    assert _extract_output_paths({}) == []
    assert _extract_output_paths({"output": ""}) == []
    assert _extract_output_paths({"outputs": [None, 42, "/tmp/c.pdf"]}) == ["/tmp/c.pdf"]


def test_register_existing_adopts_external_file(tmp_path):
    """A tool that wrote to /tmp/foo.pdf should end up as a real conversation
    file under UPLOAD_DIR/<conv>/<file_id>__foo.pdf."""
    from server import conversations as cs
    from server import files as files_store

    c = cs.create(title="t")
    src = tmp_path / "external.pdf"
    src.write_bytes(b"%PDF-1.4 stub")

    meta = files_store.register_existing(c.id, src)
    assert meta.file_id.startswith("f_")
    assert meta.name == "external.pdf"
    assert meta.size == src.stat().st_size
    assert meta.mime == "application/pdf"
    assert Path(meta.path).is_file()
    # Lives under the conversation's upload dir, NOT the original tmp_path.
    assert str(files_store.UPLOAD_DIR / c.id) in meta.path
    # Round-trips via the registry.
    assert files_store.get(meta.file_id) is meta


def test_register_existing_in_place_when_already_canonical():
    """If the agent wrote straight into the canonical location, we should
    just adopt it instead of copying."""
    from server import conversations as cs
    from server import files as files_store

    c = cs.create(title="t")
    conv_dir = files_store.UPLOAD_DIR / c.id
    conv_dir.mkdir(parents=True, exist_ok=True)
    canonical = conv_dir / "f_preexisting__hello.pdf"
    canonical.write_bytes(b"%PDF-1.4 hi")

    meta = files_store.register_existing(c.id, canonical)
    assert Path(meta.path) == canonical
    assert canonical.is_file()             # still there
    # Only one PDF in the dir (no duplicate copy).
    pdfs = list(conv_dir.glob("*.pdf"))
    assert len(pdfs) == 1


def test_materialise_file_created_attaches_and_returns_filemeta(tmp_path):
    from server import conversations as cs
    from server import runs as runs_mod

    c = cs.create(title="t")
    src = tmp_path / "out.pdf"
    src.write_bytes(b"%PDF-1.4 hello")

    ev = {
        "type": "file_created",
        "path": str(src),
        "tool_name": "pdf.create",
        "call_id": "call_x",
        "conversation_id": c.id,
    }
    out = runs_mod._materialise_file_created(ev, fallback_conv_id=None)
    assert "file" in out
    assert out["file"]["name"] == "out.pdf"
    assert out["file"]["conversation_id"] == c.id
    # The conversation now has the file attached.
    refreshed = cs.get(c.id)
    assert out["file"]["file_id"] in refreshed.file_ids


def test_materialise_file_created_uses_fallback_conv_id(tmp_path):
    """If the worker didn't tag the event with a conv id, the runs layer
    uses the one it was started with."""
    from server import conversations as cs
    from server import runs as runs_mod

    c = cs.create(title="t")
    src = tmp_path / "out.csv"
    src.write_text("a,b\n1,2\n")
    ev = {"type": "file_created", "path": str(src), "tool_name": "x", "call_id": "y"}
    out = runs_mod._materialise_file_created(ev, fallback_conv_id=c.id)
    assert "file" in out
    assert out["file"]["mime"] == "text/csv"


def test_materialise_file_created_surfaces_errors():
    from server import runs as runs_mod

    # Missing conv id and no fallback.
    out = runs_mod._materialise_file_created(
        {"type": "file_created", "path": "/tmp/whatever"}, fallback_conv_id=None,
    )
    assert "error" in out and "missing" in out["error"]

    # Path does not exist on disk.
    out = runs_mod._materialise_file_created(
        {"type": "file_created", "path": "/tmp/__definitely_not_a_real_file__.pdf",
         "conversation_id": "conv_x"},
        fallback_conv_id=None,
    )
    assert "error" in out and "no longer exists" in out["error"]


def test_download_endpoint_returns_bytes(tmp_path):
    from fastapi.testclient import TestClient
    from server import app as app_mod
    from server import conversations as cs
    from server import files as files_store

    c = cs.create(title="t")
    meta = files_store.save(
        conversation_id=c.id, name="hello.txt", mime="text/plain", data=b"hello world",
    )

    client = TestClient(app_mod.app)
    r = client.get(f"/api/files/{meta.file_id}/download")
    assert r.status_code == 200
    assert r.content == b"hello world"
    assert "hello.txt" in r.headers.get("content-disposition", "")
    assert r.headers["content-type"].startswith("text/plain")


def test_download_endpoint_404():
    from fastapi.testclient import TestClient
    from server import app as app_mod

    client = TestClient(app_mod.app)
    r = client.get("/api/files/f_nope/download")
    assert r.status_code == 404
