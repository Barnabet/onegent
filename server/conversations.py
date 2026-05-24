"""
Server-side conversation store.

A conversation is the persistent thread the user has with the orchestrator:
a list of `(user, assistant)` message pairs plus the set of file_ids
attached to the thread. Persisted as one JSON file per conversation under
CONVERSATIONS_DIR. In-memory dict on top for fast list/get.

The store is the bridge between the stateless `POST /api/runs` model and
a real chat experience — on each run the server loads the conversation's
prior transcript and passes it as `history` to the worker.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


REPO = Path(__file__).resolve().parent.parent
CONVERSATIONS_DIR = Path(
    os.environ.get("CONVERSATIONS_DIR", REPO / "conversations")
)


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    ts: float
    run_id: Optional[str] = None  # set on assistant messages


@dataclass
class Conversation:
    id: str
    title: str
    created_at: float
    updated_at: float
    messages: List[Message] = field(default_factory=list)
    # file_ids attached to this conversation. Files themselves live in
    # server/files.py keyed by conversation_id == this id.
    file_ids: List[str] = field(default_factory=list)


_CONVS: Dict[str, Conversation] = {}
_LOCK = threading.Lock()
_LOADED = False


def _path_for(conv_id: str) -> Path:
    return CONVERSATIONS_DIR / f"{conv_id}.json"


def _to_dict(c: Conversation) -> dict:
    d = asdict(c)
    return d


def _from_dict(d: dict) -> Conversation:
    msgs = [Message(**m) for m in d.get("messages", [])]
    return Conversation(
        id=d["id"],
        title=d.get("title", ""),
        created_at=d.get("created_at", 0.0),
        updated_at=d.get("updated_at", d.get("created_at", 0.0)),
        messages=msgs,
        file_ids=list(d.get("file_ids", [])),
    )


def _persist(c: Conversation) -> None:
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path_for(c.id).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_to_dict(c), indent=2), encoding="utf-8")
    tmp.replace(_path_for(c.id))


def _load_all() -> None:
    """Hydrate the in-memory dict from disk. Idempotent."""
    global _LOADED
    if _LOADED:
        return
    if CONVERSATIONS_DIR.is_dir():
        for p in CONVERSATIONS_DIR.glob("conv_*.json"):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                c = _from_dict(d)
                _CONVS[c.id] = c
            except Exception:
                continue
    _LOADED = True


def _ensure_loaded() -> None:
    with _LOCK:
        _load_all()


def create(title: Optional[str] = None) -> Conversation:
    _ensure_loaded()
    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    now = time.time()
    c = Conversation(
        id=conv_id,
        title=title or "New conversation",
        created_at=now,
        updated_at=now,
    )
    with _LOCK:
        _CONVS[conv_id] = c
        _persist(c)
    return c


def list_all() -> List[Conversation]:
    _ensure_loaded()
    with _LOCK:
        return sorted(_CONVS.values(), key=lambda c: c.updated_at, reverse=True)


def get(conv_id: str) -> Optional[Conversation]:
    _ensure_loaded()
    with _LOCK:
        return _CONVS.get(conv_id)


def delete(conv_id: str) -> bool:
    _ensure_loaded()
    with _LOCK:
        c = _CONVS.pop(conv_id, None)
    if c is None:
        return False
    try:
        _path_for(conv_id).unlink(missing_ok=True)
    except Exception:
        pass
    return True


def rename(conv_id: str, title: str) -> Optional[Conversation]:
    _ensure_loaded()
    with _LOCK:
        c = _CONVS.get(conv_id)
        if c is None:
            return None
        c.title = title.strip() or c.title
        c.updated_at = time.time()
        _persist(c)
        return c


def append_message(
    conv_id: str,
    role: str,
    content: str,
    run_id: Optional[str] = None,
) -> Optional[Conversation]:
    _ensure_loaded()
    with _LOCK:
        c = _CONVS.get(conv_id)
        if c is None:
            return None
        c.messages.append(
            Message(role=role, content=content, ts=time.time(), run_id=run_id)
        )
        c.updated_at = time.time()
        # If the title is still the default and this is the first user
        # message, derive a short title from it.
        if (
            role == "user"
            and c.title == "New conversation"
            and sum(1 for m in c.messages if m.role == "user") == 1
        ):
            snippet = content.strip().splitlines()[0][:60].strip()
            if snippet:
                c.title = snippet + ("…" if len(content) > 60 else "")
        _persist(c)
        return c


def attach_file(conv_id: str, file_id: str) -> Optional[Conversation]:
    _ensure_loaded()
    with _LOCK:
        c = _CONVS.get(conv_id)
        if c is None:
            return None
        if file_id not in c.file_ids:
            c.file_ids.append(file_id)
            c.updated_at = time.time()
            _persist(c)
        return c


def detach_file(conv_id: str, file_id: str) -> Optional[Conversation]:
    _ensure_loaded()
    with _LOCK:
        c = _CONVS.get(conv_id)
        if c is None:
            return None
        if file_id in c.file_ids:
            c.file_ids.remove(file_id)
            c.updated_at = time.time()
            _persist(c)
        return c


def history_for_llm(conv_id: str) -> List[dict]:
    """Return prior (user, assistant) pairs as plain {role, content} dicts.

    Suitable for seeding `subagent.run(history=...)`. Excludes any
    in-progress turn — the caller appends the new user message after.
    """
    c = get(conv_id)
    if c is None:
        return []
    return [{"role": m.role, "content": m.content} for m in c.messages]


def to_dict(c: Conversation) -> dict:
    return _to_dict(c)


def summary_dict(c: Conversation) -> dict:
    """Lightweight view for the list endpoint."""
    return {
        "id": c.id,
        "title": c.title,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "message_count": len(c.messages),
        "file_count": len(c.file_ids),
    }
