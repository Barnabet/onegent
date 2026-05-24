"""
Scoring engine. Pure functions that take a run's transcript (events + final
text) and an assertion, and return an AssertionResult.

The transcript is just the list of dicts emitted by the supervisor — no
dependency on the supervisor itself, so this module is unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from evals.case import (
    ContainsAssertion,
    JudgeAssertion,
    NoErrorAssertion,
    RegexAssertion,
    ToolCalledAssertion,
    ToolNotCalledAssertion,
)


# --- Transcript view --------------------------------------------------------


@dataclass
class Transcript:
    final_text: str
    events: List[dict]
    error: Optional[str] = None

    def tool_calls(self) -> List[dict]:
        return [e for e in self.events if e.get("type") == "tool_call"]

    def tool_calls_named(self, name: str) -> List[dict]:
        return [e for e in self.tool_calls() if e.get("name") == name]


# --- Result -----------------------------------------------------------------


@dataclass
class AssertionResult:
    kind: str
    passed: bool
    detail: str = ""
    # For judge assertions only:
    score: Optional[int] = None
    rationale: Optional[str] = None


# --- Deterministic scorers --------------------------------------------------


def _score_contains(t: Transcript, a: ContainsAssertion) -> AssertionResult:
    haystack = t.final_text if a.case_sensitive else t.final_text.lower()
    needle = a.text if a.case_sensitive else a.text.lower()
    ok = needle in haystack
    return AssertionResult(
        kind=a.kind,
        passed=ok,
        detail=("found" if ok else f"missing substring {a.text!r}"),
    )


_REGEX_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


def _score_regex(t: Transcript, a: RegexAssertion) -> AssertionResult:
    flags = 0
    for f in a.flags:
        flags |= _REGEX_FLAGS.get(f.lower(), 0)
    ok = re.search(a.pattern, t.final_text, flags) is not None
    return AssertionResult(
        kind=a.kind,
        passed=ok,
        detail=("matched" if ok else f"no match for /{a.pattern}/"),
    )


def _args_match(actual: dict, expected: dict) -> bool:
    """Shallow subset check — every key in `expected` must equal `actual`'s."""
    for k, v in expected.items():
        if k not in actual or actual[k] != v:
            return False
    return True


def _score_tool_called(t: Transcript, a: ToolCalledAssertion) -> AssertionResult:
    calls = t.tool_calls_named(a.name)
    if a.args_contains is not None:
        calls = [c for c in calls if _args_match(c.get("args") or {}, a.args_contains)]
    ok = len(calls) >= a.min_times
    return AssertionResult(
        kind=a.kind,
        passed=ok,
        detail=f"observed {len(calls)} matching call(s), needed >= {a.min_times}",
    )


def _score_tool_not_called(t: Transcript, a: ToolNotCalledAssertion) -> AssertionResult:
    calls = t.tool_calls_named(a.name)
    ok = len(calls) == 0
    return AssertionResult(
        kind=a.kind,
        passed=ok,
        detail=("not called" if ok else f"called {len(calls)} time(s)"),
    )


def _score_no_error(t: Transcript, _a: NoErrorAssertion) -> AssertionResult:
    if t.error:
        return AssertionResult(kind="no_error", passed=False, detail=t.error)
    err_events = [e for e in t.events if e.get("type") == "error"]
    if err_events:
        return AssertionResult(
            kind="no_error",
            passed=False,
            detail=err_events[0].get("message", "error event in transcript"),
        )
    return AssertionResult(kind="no_error", passed=True, detail="no errors")


# --- Public entry point -----------------------------------------------------


def score_assertion(
    t: Transcript,
    a: Any,
    judge_fn: Optional[Callable[[Transcript, JudgeAssertion], AssertionResult]] = None,
) -> AssertionResult:
    """Dispatch to the right scorer. `judge_fn` is injected to keep this pure."""
    if isinstance(a, ContainsAssertion):
        return _score_contains(t, a)
    if isinstance(a, RegexAssertion):
        return _score_regex(t, a)
    if isinstance(a, ToolCalledAssertion):
        return _score_tool_called(t, a)
    if isinstance(a, ToolNotCalledAssertion):
        return _score_tool_not_called(t, a)
    if isinstance(a, NoErrorAssertion):
        return _score_no_error(t, a)
    if isinstance(a, JudgeAssertion):
        if judge_fn is None:
            return AssertionResult(
                kind="judge",
                passed=False,
                detail="judge disabled (no judge_fn provided)",
            )
        return judge_fn(t, a)
    return AssertionResult(
        kind=getattr(a, "kind", "unknown"),
        passed=False,
        detail=f"unknown assertion type {type(a).__name__}",
    )
