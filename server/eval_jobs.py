"""
Background eval jobs. Same pattern as server.runs but for the eval runner —
streams per-case results as each case finishes.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Set

from evals import case as case_mod
from evals import runner as runner_mod


@dataclass
class LiveEvalJob:
    job_id: str
    pack: Optional[str]
    case: Optional[str]
    use_judge: bool
    started_at: float
    status: str = "running"  # running | done | error
    error: Optional[str] = None
    case_results: List[dict] = field(default_factory=list)
    subscribers: Set[asyncio.Queue] = field(default_factory=set)
    loop: Optional[asyncio.AbstractEventLoop] = None
    finished: bool = False


_JOBS: Dict[str, LiveEvalJob] = {}
_LOCK = threading.Lock()


def get(job_id: str) -> Optional[LiveEvalJob]:
    with _LOCK:
        return _JOBS.get(job_id)


def all_jobs() -> List[LiveEvalJob]:
    with _LOCK:
        return list(_JOBS.values())


def _push(job: LiveEvalJob, event: dict) -> None:
    if job.loop is None:
        return
    for q in list(job.subscribers):
        try:
            job.loop.call_soon_threadsafe(q.put_nowait, event)
        except RuntimeError:
            pass


def start_job(
    pack: Optional[str],
    case: Optional[str],
    use_judge: bool,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> LiveEvalJob:
    cases = case_mod.discover_cases(pack=pack, case_id=case)
    job_id = f"eval_{uuid.uuid4().hex[:12]}"
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
    job = LiveEvalJob(
        job_id=job_id,
        pack=pack,
        case=case,
        use_judge=use_judge,
        started_at=time.time(),
        loop=loop,
    )
    with _LOCK:
        _JOBS[job_id] = job

    if not cases:
        job.status = "error"
        job.error = "no cases matched"
        job.finished = True
        return job

    def on_case_done(cr) -> None:
        d = cr.to_dict()
        job.case_results.append(d)
        _push(job, {"type": "case_done", "result": d})

    def worker() -> None:
        try:
            _push(job, {"type": "job_started", "total": len(cases)})
            runner_mod.run_suite(cases, use_judge=use_judge, on_case_done=on_case_done)
            passed = sum(1 for c in job.case_results if c["passed"])
            _push(job, {"type": "job_done", "total": len(cases), "passed": passed})
            job.status = "done"
        except Exception as e:
            job.error = f"{type(e).__name__}: {e}"
            job.status = "error"
            _push(job, {"type": "error", "message": job.error})
        finally:
            job.finished = True
            _push(job, {"type": "__end__"})

    threading.Thread(target=worker, name=f"eval-{job_id}", daemon=True).start()
    return job


async def subscribe(job: LiveEvalJob) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    # Replay
    q.put_nowait({"type": "job_started", "total": -1})
    for cr in job.case_results:
        q.put_nowait({"type": "case_done", "result": cr})
    if job.finished:
        q.put_nowait({"type": "__end__"})
    else:
        job.subscribers.add(q)
    return q


def unsubscribe(job: LiveEvalJob, q: asyncio.Queue) -> None:
    job.subscribers.discard(q)
