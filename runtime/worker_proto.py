"""
Event protocol between supervisor (parent) and sub-agent worker (child).

Events are plain dicts, JSON-serialisable. We use dicts (not dataclasses) to
keep the multiprocessing.Pipe payload trivially picklable across Python
versions.
"""

from __future__ import annotations

from typing import Any


# Event types the supervisor may receive from a worker.
EV_MODEL_TEXT = "model_text"
EV_TOOL_CALL = "tool_call"
EV_TOOL_RESULT = "tool_result"
EV_DONE = "done"
EV_ERROR = "error"


def model_text(delta: str) -> dict:
    return {"type": EV_MODEL_TEXT, "delta": delta}


def tool_call(name: str, args: dict, call_id: str) -> dict:
    return {"type": EV_TOOL_CALL, "name": name, "args": args, "call_id": call_id}


def tool_result(name: str, call_id: str, ok: bool, payload: Any) -> dict:
    return {"type": EV_TOOL_RESULT, "name": name, "call_id": call_id, "ok": ok, "payload": payload}


def done(final: str, stats: dict) -> dict:
    return {"type": EV_DONE, "final": final, "stats": stats}


def error(message: str, trace: str = "") -> dict:
    return {"type": EV_ERROR, "message": message, "trace": trace}
