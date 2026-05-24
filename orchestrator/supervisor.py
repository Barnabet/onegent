"""
Supervisor — parent process. Spawns one worker per request, pumps events,
returns the final reply.

The router is intentionally trivial in PR #2: the caller passes the pack
name directly. Routing logic will land later.
"""

from __future__ import annotations

import multiprocessing as mp
import uuid
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from runtime import worker_proto
from orchestrator.worker_entry import WorkerJob, worker_main


@dataclass
class RunResult:
    run_id: str
    final_text: str
    events: List[dict] = field(default_factory=list)
    error: Optional[str] = None
    stats: Optional[dict] = None


def run(
    pack_name: str,
    user_message: str,
    user_id: str = "local",
    on_event: Optional[Callable[[dict], None]] = None,
    run_id: Optional[str] = None,
    timeout: Optional[float] = None,
    allowed_packs: Optional[List[str]] = None,
) -> RunResult:
    """Spawn a worker, collect events to completion, return the final reply."""
    rid = run_id or f"run_{uuid.uuid4().hex[:12]}"
    mp_ctx = mp.get_context("spawn")
    parent_conn, child_conn = mp_ctx.Pipe(duplex=False)

    job = WorkerJob(
        run_id=rid,
        pack_name=pack_name,
        user_id=user_id,
        user_message=user_message,
        allowed_packs=allowed_packs,
    )

    proc = mp_ctx.Process(target=worker_main, args=(child_conn, job), daemon=True)
    proc.start()
    # The child owns its end; the parent doesn't need it.
    child_conn.close()

    result = RunResult(run_id=rid, final_text="")
    final_text_parts: List[str] = []

    try:
        while True:
            if timeout is not None and not parent_conn.poll(timeout):
                result.error = f"Worker timed out after {timeout}s"
                proc.terminate()
                break
            try:
                event = parent_conn.recv()
            except EOFError:
                break

            result.events.append(event)
            if on_event is not None:
                on_event(event)

            etype = event.get("type")
            if etype == worker_proto.EV_MODEL_TEXT:
                final_text_parts.append(event.get("delta", ""))
            elif etype == worker_proto.EV_ERROR:
                result.error = event.get("message", "unknown error")
                break
            elif etype == worker_proto.EV_DONE:
                result.stats = event.get("stats")
                break
    finally:
        proc.join(timeout=5)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2)
        parent_conn.close()

    # The model's last text response is the final reply.
    result.final_text = final_text_parts[-1] if final_text_parts else ""
    return result
