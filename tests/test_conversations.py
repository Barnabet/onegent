"""Conversation store + history-threading tests.

No LLM, no worker — we exercise the conv_store API directly and assert
that `server.app.start_run` plumbs `history` into the worker correctly
by stubbing `runs.start_run`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_conv_dir(tmp_path, monkeypatch):
    """Each test gets its own conversations dir + fresh in-memory cache."""
    monkeypatch.setenv("CONVERSATIONS_DIR", str(tmp_path / "conversations"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    # Force module reload so the env var is picked up.
    import importlib
    from server import conversations, files
    importlib.reload(conversations)
    importlib.reload(files)
    yield


def test_create_list_get_delete():
    from server import conversations as cs

    a = cs.create()
    b = cs.create(title="Manual title")
    assert a.id != b.id
    assert b.title == "Manual title"

    listed = cs.list_all()
    assert {c.id for c in listed} == {a.id, b.id}

    got = cs.get(a.id)
    assert got is not None and got.id == a.id

    assert cs.delete(a.id) is True
    assert cs.get(a.id) is None
    assert cs.delete(a.id) is False  # second delete = no-op


def test_persistence_survives_reload(tmp_path, monkeypatch):
    from server import conversations as cs

    c = cs.create(title="Persisted")
    cs.append_message(c.id, "user", "hello")
    cs.append_message(c.id, "assistant", "hi", run_id="run_x")

    # Reload the module — simulates a server restart.
    import importlib
    importlib.reload(cs)

    got = cs.get(c.id)
    assert got is not None
    assert got.title == "Persisted"
    assert [(m.role, m.content) for m in got.messages] == [
        ("user", "hello"),
        ("assistant", "hi"),
    ]
    assert got.messages[1].run_id == "run_x"


def test_auto_title_from_first_user_message():
    from server import conversations as cs

    c = cs.create()
    assert c.title == "New conversation"
    cs.append_message(c.id, "user", "Draft a credit memo for Acme SpA")
    got = cs.get(c.id)
    assert got.title.startswith("Draft a credit memo")


def test_history_for_llm_returns_role_content_pairs():
    from server import conversations as cs

    c = cs.create()
    cs.append_message(c.id, "user", "hi")
    cs.append_message(c.id, "assistant", "hello")
    cs.append_message(c.id, "user", "follow-up")
    cs.append_message(c.id, "assistant", "answer")

    hist = cs.history_for_llm(c.id)
    assert hist == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "follow-up"},
        {"role": "assistant", "content": "answer"},
    ]


def test_attach_detach_files_dedup():
    from server import conversations as cs

    c = cs.create()
    cs.attach_file(c.id, "f_1")
    cs.attach_file(c.id, "f_2")
    cs.attach_file(c.id, "f_1")  # duplicate
    assert cs.get(c.id).file_ids == ["f_1", "f_2"]

    cs.detach_file(c.id, "f_1")
    assert cs.get(c.id).file_ids == ["f_2"]


def test_start_run_threads_history_and_files(monkeypatch):
    """The HTTP layer must load the conversation's history + files into the run."""
    from fastapi.testclient import TestClient

    # Stub runs.start_run BEFORE the app routes it.
    from server import app as app_mod
    from server import conversations as cs
    from server import files as files_store

    captured = {}

    class _StubRun:
        def __init__(self):
            self.run_id = "run_stub"
            self.pack = "router"
            self.user_message = ""
            self.user_id = "webui"
            self.started_at = 0.0
            self.status = "running"
            self.error = None
            self.final_text = ""
            self.stats = None
            self.events = []

    def fake_start_run(pack, user_message, user_id, **kwargs):
        captured["pack"] = pack
        captured["user_message"] = user_message
        captured["history"] = kwargs.get("history")
        captured["files"] = kwargs.get("files")
        captured["allowed_packs"] = kwargs.get("allowed_packs")
        return _StubRun()

    monkeypatch.setattr(app_mod.runs, "start_run", fake_start_run)

    client = TestClient(app_mod.app)

    # Set up a conversation with prior history + an attached file.
    c = cs.create(title="t")
    cs.append_message(c.id, "user", "first question")
    cs.append_message(c.id, "assistant", "first answer", run_id="run_prev")
    meta = files_store.save(
        conversation_id=c.id, name="a.txt", mime="text/plain", data=b"hi"
    )
    cs.attach_file(c.id, meta.file_id)

    # Fire the next turn.
    r = client.post(
        "/api/runs",
        json={"user_message": "second question", "conversation_id": c.id},
    )
    assert r.status_code == 200, r.text

    # History reflects only the PRIOR turn (the new user message goes in
    # via `user_message`, not via history).
    assert captured["history"] == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
    ]
    assert captured["user_message"] == "second question"
    # The conversation's attached file was forwarded.
    assert captured["files"] is not None and len(captured["files"]) == 1
    assert captured["files"][0]["file_id"] == meta.file_id

    # The new user turn was recorded immediately (assistant turn waits for
    # the on_done callback, which our stub never triggers).
    got = cs.get(c.id)
    assert [m.role for m in got.messages] == ["user", "assistant", "user"]
    assert got.messages[-1].content == "second question"


def test_start_run_404_on_missing_conversation():
    from fastapi.testclient import TestClient
    from server import app as app_mod

    client = TestClient(app_mod.app)
    r = client.post(
        "/api/runs",
        json={"user_message": "x", "conversation_id": "conv_nope"},
    )
    assert r.status_code == 404


def test_upload_requires_existing_conversation():
    from fastapi.testclient import TestClient
    from server import app as app_mod

    client = TestClient(app_mod.app)
    r = client.post(
        "/api/files",
        data={"conversation_id": "conv_nope"},
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert r.status_code == 404


def test_upload_attaches_file_to_conversation():
    from fastapi.testclient import TestClient
    from server import app as app_mod
    from server import conversations as cs

    client = TestClient(app_mod.app)
    c = cs.create()

    r = client.post(
        "/api/files",
        data={"conversation_id": c.id},
        files={"file": ("x.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 200
    fid = r.json()["file_id"]
    assert cs.get(c.id).file_ids == [fid]

    # Deleting the file detaches it.
    r = client.delete(f"/api/files/{fid}")
    assert r.status_code == 200
    assert cs.get(c.id).file_ids == []
