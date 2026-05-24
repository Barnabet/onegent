"""
Eval runner. Runs N cases, scoring each one and producing a summary.

For each case:
  1. Invoke supervisor.run(pack, user_message, timeout) — one full sub-agent run.
  2. Build a Transcript from the result.
  3. Score every assertion (judge assertions optional via `use_judge`).
  4. Emit a CaseResult.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from evals.case import EvalCase, JudgeAssertion
from evals.judge import make_judge
from evals.score import AssertionResult, Transcript, score_assertion
from orchestrator import supervisor


@dataclass
class CaseResult:
    case_id: str
    pack: str
    run_id: str
    passed: bool
    duration_s: float
    final_text: str
    assertion_results: List[AssertionResult] = field(default_factory=list)
    error: Optional[str] = None
    stats: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["assertion_results"] = [asdict(r) for r in self.assertion_results]
        return d


@dataclass
class SuiteResult:
    cases: List[CaseResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.cases if not c.passed)

    @property
    def total(self) -> int:
        return len(self.cases)


def run_case(case: EvalCase, *, use_judge: bool = True) -> CaseResult:
    """Run one case end-to-end and score it."""
    t0 = time.time()
    run_result = supervisor.run(
        pack_name=case.pack,
        user_message=case.user_message,
        user_id="evals",
        timeout=case.timeout,
    )
    duration = time.time() - t0

    transcript = Transcript(
        final_text=run_result.final_text,
        events=run_result.events,
        error=run_result.error,
    )

    judge_fn = make_judge(case.user_message) if use_judge else None

    assertion_results: List[AssertionResult] = []
    for a in case.assertions:
        if isinstance(a, JudgeAssertion) and not use_judge:
            assertion_results.append(
                AssertionResult(kind="judge", passed=True, detail="(skipped: --no-judge)")
            )
            continue
        assertion_results.append(score_assertion(transcript, a, judge_fn=judge_fn))

    all_passed = all(r.passed for r in assertion_results) and run_result.error is None

    return CaseResult(
        case_id=case.id,
        pack=case.pack,
        run_id=run_result.run_id,
        passed=all_passed,
        duration_s=round(duration, 3),
        final_text=run_result.final_text,
        assertion_results=assertion_results,
        error=run_result.error,
        stats=run_result.stats,
    )


def run_suite(cases: List[EvalCase], *, use_judge: bool = True, on_case_done=None) -> SuiteResult:
    suite = SuiteResult()
    for case in cases:
        cr = run_case(case, use_judge=use_judge)
        suite.cases.append(cr)
        if on_case_done is not None:
            on_case_done(cr)
    return suite
