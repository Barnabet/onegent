"""
LLM-as-judge assertion. Calls the same chat() endpoint with a fixed rubric
that demands a strict JSON response: {"score": 1..5, "rationale": "..."}.

The judge sees the user message, the final reply, a tool-call summary, and
the criterion. It does NOT see raw tool payloads (too noisy, often huge).
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from evals.case import JudgeAssertion
from evals.score import AssertionResult, Transcript
from runtime import llm


JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", llm.DEFAULT_MODEL)


_SYSTEM = """You are an impartial evaluator scoring a single response from a
sub-agent. You will be given:
  - the user's original message,
  - the agent's final reply,
  - a brief list of tools the agent called (names + arg keys only),
  - a single rubric criterion to judge against.

Score the reply against the criterion on this 1-5 scale:
  5 - fully meets the criterion, no caveats
  4 - meets the criterion with only minor issues
  3 - partially meets the criterion
  2 - largely misses the criterion
  1 - completely fails the criterion

Reply with STRICT JSON only, no prose, no markdown fence:
  {"score": <int 1-5>, "rationale": "<one or two sentences>"}
"""


def _tool_summary(t: Transcript) -> str:
    calls = t.tool_calls()
    if not calls:
        return "(no tools called)"
    lines = []
    for c in calls:
        args = c.get("args") or {}
        keys = ", ".join(sorted(args.keys())) if args else "-"
        lines.append(f"- {c.get('name')}(args: {keys})")
    return "\n".join(lines)


def _build_user_message(t: Transcript, criterion: str, user_message: str) -> str:
    return (
        f"USER MESSAGE:\n{user_message}\n\n"
        f"AGENT FINAL REPLY:\n{t.final_text}\n\n"
        f"TOOLS CALLED:\n{_tool_summary(t)}\n\n"
        f"CRITERION:\n{criterion}"
    )


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_judgment(text: str) -> tuple[Optional[int], str]:
    """Extract {"score":int,"rationale":str} from the judge reply, tolerantly."""
    if not text:
        return None, "judge returned empty response"
    m = _JSON_RE.search(text)
    if not m:
        return None, f"judge response not JSON: {text[:200]}"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return None, f"judge JSON parse error: {e}; raw: {text[:200]}"
    score = obj.get("score")
    rationale = str(obj.get("rationale") or "").strip()
    if not isinstance(score, int) or not (1 <= score <= 5):
        return None, f"judge returned invalid score: {score!r}"
    return score, rationale


def make_judge(user_message_for_case: str, model: Optional[str] = None):
    """Return a judge_fn bound to the user message of one specific case."""

    def judge_fn(t: Transcript, a: JudgeAssertion) -> AssertionResult:
        try:
            resp = llm.chat(
                messages=[{"role": "user", "content": _build_user_message(t, a.criterion, user_message_for_case)}],
                model=model or JUDGE_MODEL,
                system=_SYSTEM,
            )
        except Exception as e:
            return AssertionResult(
                kind="judge",
                passed=False,
                detail=f"judge call failed: {type(e).__name__}: {e}",
            )
        score, rationale = _parse_judgment(resp.text or "")
        if score is None:
            return AssertionResult(kind="judge", passed=False, detail=rationale)
        passed = score >= a.threshold
        return AssertionResult(
            kind="judge",
            passed=passed,
            detail=f"score {score}/5 (threshold {a.threshold})",
            score=score,
            rationale=rationale,
        )

    return judge_fn
