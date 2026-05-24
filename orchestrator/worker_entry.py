"""
Child-process entry point. Spawned by supervisor.spawn().

Receives a WorkerJob over a multiprocessing.Pipe connection, runs the
sub-agent loop, and emits events back through the same connection.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Optional

from runtime import tool_registry, worker_proto
from runtime.audit import AuditLogger
from runtime.pack_loader import bind, load as load_pack
from runtime.tool_registry import ToolCtx
from orchestrator import subagent


@dataclass
class WorkerJob:
    run_id: str
    pack_name: str
    user_id: str
    user_message: str


def worker_main(conn: Connection, job: WorkerJob) -> None:
    """Top-level child entry. Always closes the connection on exit."""
    try:
        _run(conn, job)
    except Exception as e:  # last-chance trap; everything below should catch its own
        try:
            conn.send(worker_proto.error(str(e), traceback.format_exc()))
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _run(conn: Connection, job: WorkerJob) -> None:
    audit = AuditLogger(run_id=job.run_id, pack=job.pack_name, user_id=job.user_id)
    audit("worker_start", user_message=job.user_message)

    # Discover tools and bind the pack inside the child so the parent's
    # registry state never leaks across runs.
    tool_registry.discover()
    pack = load_pack(job.pack_name)
    bound = bind(pack)
    audit(
        "pack_bound",
        skills=[s.frontmatter.name for s in bound.skills],
        tools=bound.tools,
        effective_classification=bound.effective_classification,
    )

    ctx = ToolCtx(
        run_id=job.run_id,
        user_id=job.user_id,
        pack_name=pack.name,
        classification_ceiling=pack.classification,
        allowed_data_sources=pack.allowed_data_sources,
        audit=audit,
    )

    def emit(event: dict) -> None:
        # Audit every emitted event in addition to forwarding it.
        audit(event["type"], **{k: v for k, v in event.items() if k != "type"})
        conn.send(event)

    try:
        stats = subagent.run(bound, job.user_message, ctx, emit)
    except Exception as e:
        emit(worker_proto.error(str(e), traceback.format_exc()))
        return

    # The final reply is the last model_text emitted; subagent.run does not
    # currently aggregate it, so we recompute it here for the done event.
    # Simpler approach: pass an empty final and let the supervisor stitch.
    emit(
        worker_proto.done(
            final="",
            stats={
                "turns": stats.turns,
                "tool_calls": stats.tool_calls,
                "finish_reason": stats.final_finish_reason,
            },
        )
    )
    audit("worker_done", **{
        "turns": stats.turns,
        "tool_calls": stats.tool_calls,
        "finish_reason": stats.final_finish_reason,
    })
