"""
File upload registry used by the chat UI.

Files are stored on disk under UPLOAD_DIR/<conversation_id>/<file_id>__<name>.
Metadata is kept in-process (small dict) so the chat can list/delete them
and pass the metadata list to the orchestrator on each run.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


REPO = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", REPO / "uploads"))


@dataclass
class FileMeta:
    file_id: str
    conversation_id: str
    name: str
    size: int
    mime: str
    uploaded_at: float
    path: str  # absolute path on disk


_FILES: Dict[str, FileMeta] = {}
_LOCK = threading.Lock()


def _safe_name(name: str) -> str:
    # Strip any path separators; keep the basename only.
    return Path(name).name or "file"


def save(conversation_id: str, name: str, mime: str, data: bytes) -> FileMeta:
    file_id = f"f_{uuid.uuid4().hex[:12]}"
    safe = _safe_name(name)
    conv_dir = UPLOAD_DIR / conversation_id
    conv_dir.mkdir(parents=True, exist_ok=True)
    dest = conv_dir / f"{file_id}__{safe}"
    dest.write_bytes(data)
    meta = FileMeta(
        file_id=file_id,
        conversation_id=conversation_id,
        name=safe,
        size=len(data),
        mime=mime or "application/octet-stream",
        uploaded_at=time.time(),
        path=str(dest),
    )
    with _LOCK:
        _FILES[file_id] = meta
    return meta


def list_for(conversation_id: str) -> List[FileMeta]:
    with _LOCK:
        return sorted(
            (m for m in _FILES.values() if m.conversation_id == conversation_id),
            key=lambda m: m.uploaded_at,
        )


def get(file_id: str) -> Optional[FileMeta]:
    with _LOCK:
        return _FILES.get(file_id)


def delete(file_id: str) -> bool:
    with _LOCK:
        meta = _FILES.pop(file_id, None)
    if meta is None:
        return False
    try:
        Path(meta.path).unlink(missing_ok=True)
    except Exception:
        pass
    return True


def to_dict(meta: FileMeta) -> dict:
    return asdict(meta)
