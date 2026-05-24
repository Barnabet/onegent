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


_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".html": "text/html",
}


def _guess_mime(name: str) -> str:
    return _MIME_BY_EXT.get(Path(name).suffix.lower(), "application/octet-stream")


def register_existing(conversation_id: str, src: Path, name: Optional[str] = None) -> FileMeta:
    """Adopt a file already on disk as a conversation attachment.

    Used by the runs layer when a tool writes a file (e.g. ``pdf.create``,
    ``xlsx.write``). The file is moved into ``UPLOAD_DIR/<conv>/`` under
    the standard ``<file_id>__<name>`` naming so the existing download /
    list / delete code paths work without special-casing agent outputs.

    If ``src`` already lives inside the conversation's upload dir under the
    canonical naming (e.g. the agent wrote straight there), we just adopt
    it in place instead of moving.
    """
    if not src.is_file():
        raise FileNotFoundError(f"No file at {src}")
    safe = _safe_name(name or src.name)
    file_id = f"f_{uuid.uuid4().hex[:12]}"
    conv_dir = UPLOAD_DIR / conversation_id
    conv_dir.mkdir(parents=True, exist_ok=True)

    canonical = conv_dir / f"{file_id}__{safe}"
    try:
        src_resolved = src.resolve()
    except Exception:
        src_resolved = src
    if src_resolved.parent == conv_dir.resolve() and "__" in src.name:
        # Already in the right place under the right naming — adopt in place.
        canonical = src
    else:
        canonical.write_bytes(src.read_bytes())

    meta = FileMeta(
        file_id=file_id,
        conversation_id=conversation_id,
        name=safe,
        size=canonical.stat().st_size,
        mime=_guess_mime(safe),
        uploaded_at=time.time(),
        path=str(canonical),
    )
    with _LOCK:
        _FILES[file_id] = meta
    return meta


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
