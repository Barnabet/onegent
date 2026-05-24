"""
In-process registry of live + completed supervisor runs.

A run is launched on a background thread. Events are pushed into an
asyncio.Queue per subscriber so multiple HTTP clients can fan-out. The
final RunResult is stored on completion.
"""

from __future__ import annotations

import asyncio
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from orchestrator import supervisor


@dataclass
class LiveRun:
    run_id: str
    pack: str
    user_message: str
    user_id: str
    started_at: float
    status: str = "running"  # running | done | error
    error: Optional[str] = None
    final_text: str = ""
    stats: Optional[dict] = None
    events: List[dict] = field(default_factory=list)
    # Subscriber queues — each SSE client gets its own.
    subscribers: Set[asyncio.Queue] = field(default_factory=set)
    # The event loop the queues live on, so the worker thread can push.
    loop: Optional[asyncio.AbstractEventLoop] = None
    finished: bool = False


_RUNS: Dict[str, LiveRun] = {}
_LOCK = threading.Lock()


def get(run_id: str) -> Optional[LiveRun]:
    with _LOCK:
        return _RUNS.get(run_id)


def all_runs() -> List[LiveRun]:
    with _LOCK:
        return list(_RUNS.values())


def _push_event_to_subscribers(run: LiveRun, event: dict) -> None:
    """Called from the worker thread. Schedules queue.put on the asyncio loop."""
    if run.loop is None:
        return
    for q in list(run.subscribers):
        try:
            run.loop.call_soon_threadsafe(q.put_nowait, event)
        except RuntimeError:
            pass  # loop closed; subscriber will time out


def start_run(
    pack: str,
    user_message: str,
    user_id: str = "webui",
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> LiveRun:
    """Spawn a supervisor run on a background thread. Returns the LiveRun handle.

    `loop` must be the asyncio loop that SSE subscribers will run on; the
    worker thread uses it to thread-safe-schedule queue puts. If omitted, we
    try to grab the running loop (only works when called from async context).
    """
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
    run = LiveRun(
        run_id=run_id,
        pack=pack,
        user_message=user_message,
        user_id=user_id,
        started_at=time.time(),
        loop=loop,
    )
    with _LOCK:
        _RUNS[run_id] = run

    def on_event(ev: dict) -> None:
        run.events.append(ev)
        _push_event_to_subscribers(run, ev)

    def worker() -> None:
        try:
            result = supervisor.run(
                pack_name=pack,
                user_message=user_message,
                user_id=user_id,
                on_event=on_event,
                run_id=run_id,
                timeout=300.0,
            )
            run.final_text = result.final_text
            run.stats = result.stats
            run.error = result.error
            run.status = "error" if result.error else "done"
        except Exception as e:
            run.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            run.status = "error"
        finally:
            run.finished = True
            # Sentinel so SSE subscribers can detach.
            _push_event_to_subscribers(run, {"type": "__end__"})

    t = threading.Thread(target=worker, name=f"run-{run_id}", daemon=True)
    t.start()
    return run


async def subscribe(run: LiveRun) -> asyncio.Queue:
    """Create a queue prefilled with the events already received, then attach."""
    q: asyncio.Queue = asyncio.Queue()
    # Replay buffered events first (so a late subscriber sees the history).
    for ev in run.events:
        q.put_nowait(ev)
    if run.finished:
        q.put_nowait({"type": "__end__"})
    else:
        run.subscribers.add(q)
    return q


def unsubscribe(run: LiveRun, q: asyncio.Queue) -> None:
    run.subscribers.discard(q)
