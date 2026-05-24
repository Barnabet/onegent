"""
Structured audit log. JSONL, one file per run, plus a single global stream.

Every event carries: ts, run_id, pack, user_id, event_type, ...fields.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional


_LOCK = threading.Lock()

DEFAULT_DIR = Path(os.environ.get("AUDIT_DIR", Path(__file__).resolve().parent.parent / "audit_logs"))


class AuditLogger:
    """Append-only JSONL writer for one run."""

    def __init__(self, run_id: str, pack: str, user_id: str, directory: Optional[Path] = None) -> None:
        self.run_id = run_id
        self.pack = pack
        self.user_id = user_id
        self.dir = Path(directory or DEFAULT_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{run_id}.jsonl"

    def __call__(self, event_type: str, **fields: Any) -> None:
        record = {
            "ts": time.time(),
            "run_id": self.run_id,
            "pack": self.pack,
            "user_id": self.user_id,
            "event_type": event_type,
            **fields,
        }
        line = json.dumps(record, default=str, ensure_ascii=False)
        with _LOCK:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def read_all(self) -> "list[dict]":
        if not self.path.is_file():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
