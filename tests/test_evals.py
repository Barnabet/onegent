"""
Offline tests for the eval harness. Exercise the case loader and scoring
engine without touching the LLM or supervisor.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from evals.case import (
    ContainsAssertion,
    JudgeAssertion,
    NoErrorAssertion,
    RegexAssertion,
    ToolCalledAssertion,
    ToolNotCalledAssertion,
    discover_cases,
    parse_case,
)
from evals.score import AssertionResult, Transcript, score_assertion


REPO = Path(__file__).resolve().parent.parent


# --- case loader ------------------------------------------------------------


def test_parse_minimal_case():
    raw = {
        "id": "x",
        "pack": "hello",
        "user_message": "hi",
        "assertions": [
            {"kind": "no_error"},
            {"kind": "contains", "text": "hello"},
            {"kind": "regex", "pattern": "\\d+", "flags": ["i"]},
            {"kind": "tool_called", "name": "core.echo", "min_times": 2},
            {"kind": "tool_not_called", "name": "repo.scaffold_tool"},
            {"kind": "judge", "criterion": "be nice", "threshold": 3},
        ],
    }
    case = parse_case(raw)
    assert case.id == "x"
    assert case.pack == "hello"
    kinds = [type(a).__name__ for a in case.assertions]
    assert kinds == [
        "NoErrorAssertion",
        "ContainsAssertion",
        "RegexAssertion",
        "ToolCalledAssertion",
        "ToolNotCalledAssertion",
        "JudgeAssertion",
    ]


def test_parse_unknown_assertion_kind_raises():
    with pytest.raises(ValueError):
        parse_case({"id": "x", "pack": "y", "user_message": "z",
                    "assertions": [{"kind": "totally_made_up"}]})


def test_discover_finds_shipped_cases():
    cases = discover_cases(root=REPO / "evals" / "cases")
    ids = [c.id for c in cases]
    assert "hello_echo_smoke" in ids
    assert "credit_word_count_doc" in ids
    assert "skill_creator_dedup_check" in ids


def test_shipped_case_yaml_files_are_valid():
    """Every shipped case file parses successfully."""
    for path in (REPO / "evals" / "cases").rglob("*.yaml"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        parse_case(raw, source_path=path)  # should not raise


# --- scoring engine ---------------------------------------------------------


def _mk_transcript(final="", events=None, error=None):
    return Transcript(final_text=final, events=events or [], error=error)


def test_contains_case_insensitive_default():
    t = _mk_transcript(final="Hello WORLD")
    r = score_assertion(t, ContainsAssertion(text="world"))
    assert r.passed
    r2 = score_assertion(t, ContainsAssertion(text="world", case_sensitive=True))
    assert not r2.passed


def test_regex_with_flags():
    t = _mk_transcript(final="line1\nLINE2")
    r = score_assertion(t, RegexAssertion(pattern="^line2$", flags=["i", "m"]))
    assert r.passed


def test_tool_called_counts():
    events = [
        {"type": "tool_call", "name": "core.echo", "args": {"text": "a"}, "call_id": "1"},
        {"type": "tool_call", "name": "core.echo", "args": {"text": "b"}, "call_id": "2"},
        {"type": "tool_call", "name": "text.word_count", "args": {"text": "x"}, "call_id": "3"},
    ]
    t = _mk_transcript(events=events)
    assert score_assertion(t, ToolCalledAssertion(name="core.echo", min_times=2)).passed
    assert not score_assertion(t, ToolCalledAssertion(name="core.echo", min_times=3)).passed
    assert score_assertion(
        t, ToolCalledAssertion(name="core.echo", args_contains={"text": "a"})
    ).passed
    assert not score_assertion(
        t, ToolCalledAssertion(name="core.echo", args_contains={"text": "z"})
    ).passed


def test_tool_not_called():
    events = [{"type": "tool_call", "name": "core.echo", "args": {}, "call_id": "1"}]
    t = _mk_transcript(events=events)
    assert score_assertion(t, ToolNotCalledAssertion(name="repo.scaffold_tool")).passed
    assert not score_assertion(t, ToolNotCalledAssertion(name="core.echo")).passed


def test_no_error_passes_when_clean():
    assert score_assertion(_mk_transcript(), NoErrorAssertion()).passed
    assert not score_assertion(_mk_transcript(error="boom"), NoErrorAssertion()).passed
    events = [{"type": "error", "message": "kaput"}]
    assert not score_assertion(_mk_transcript(events=events), NoErrorAssertion()).passed


def test_judge_disabled_returns_clear_detail():
    r = score_assertion(_mk_transcript(), JudgeAssertion(criterion="x"), judge_fn=None)
    assert not r.passed
    assert "judge disabled" in r.detail


def test_judge_with_stub_judge_fn():
    def stub(t, a):
        return AssertionResult(kind="judge", passed=True, detail="stub ok", score=5)

    r = score_assertion(_mk_transcript(), JudgeAssertion(criterion="x"), judge_fn=stub)
    assert r.passed and r.score == 5


# --- judge helpers (parse only — no network) --------------------------------


def test_judge_parse_strict_json():
    from evals.judge import _parse_judgment
    score, rationale = _parse_judgment('{"score": 4, "rationale": "good"}')
    assert score == 4 and rationale == "good"


def test_judge_parse_tolerates_surrounding_text():
    from evals.judge import _parse_judgment
    score, rationale = _parse_judgment(
        'Sure, here is my response:\n{"score": 5, "rationale": "perfect"}\nThanks!'
    )
    assert score == 5 and rationale == "perfect"


def test_judge_parse_rejects_invalid_score():
    from evals.judge import _parse_judgment
    score, _ = _parse_judgment('{"score": 9, "rationale": "x"}')
    assert score is None
    score, _ = _parse_judgment('not json at all')
    assert score is None
