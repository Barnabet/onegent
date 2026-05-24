"""
`docstore` domain — fetch documents from the bank's internal document store.

PR #3 ships a fixture-backed mock so pilots can run end-to-end without a
real backend. The interface (id-or-query, doc_type filter, latest flag) is
intentionally close to what the real backend will expose, so skills written
against this tool will not need to change.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from runtime.tool_registry import ToolCtx, ToolResult, ToolError


def _store_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "fixtures" / "docstore"


def _load_index() -> List[dict]:
    idx = _store_root() / "index.yaml"
    if not idx.is_file():
        return []
    raw = yaml.safe_load(idx.read_text(encoding="utf-8")) or {}
    return list(raw.get("docs") or [])


def fetch(params, ctx: ToolCtx) -> ToolResult:
    index = _load_index()
    if not index:
        return ToolResult(ok=False, error=ToolError(
            code="store_empty", message="Docstore has no documents indexed.", retriable=False,
        ))

    q = params.query.lower().strip()
    candidates = []
    for entry in index:
        if params.doc_type and entry.get("doc_type") != params.doc_type:
            continue
        haystack = " ".join(
            str(entry.get(k, "")).lower() for k in ("id", "entity", "doc_type")
        )
        if q in haystack:
            candidates.append(entry)

    if not candidates:
        return ToolResult(ok=False, error=ToolError(
            code="not_found", message=f"No document matched {params.query!r}.", retriable=False,
        ))

    if params.latest:
        candidates.sort(key=lambda e: e.get("published", ""), reverse=True)
    chosen = candidates[0]

    body_path = _store_root() / chosen["file"]
    if not body_path.is_file():
        return ToolResult(ok=False, error=ToolError(
            code="file_missing", message=f"Indexed file {chosen['file']!r} not on disk.", retriable=False,
        ))
    body = body_path.read_text(encoding="utf-8")

    return ToolResult(
        ok=True,
        data={
            "id": chosen["id"],
            "doc_type": chosen.get("doc_type"),
            "entity": chosen.get("entity"),
            "published": chosen.get("published"),
            "body": body,
        },
    )
