"""
Report rendering — terminal output + JSONL results file.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from evals.runner import CaseResult, SuiteResult


# ANSI helpers — disabled when stdout isn't a tty or NO_COLOR is set.
def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    import sys
    return sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _supports_color():
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(t: str) -> str:
    return _c("32", t)


def _red(t: str) -> str:
    return _c("31", t)


def _dim(t: str) -> str:
    return _c("2", t)


def _bold(t: str) -> str:
    return _c("1", t)


def print_case_result(cr: CaseResult) -> None:
    badge = _green("PASS") if cr.passed else _red("FAIL")
    head = f"{badge}  {_bold(cr.case_id)} [{cr.pack}]  {cr.duration_s}s  run={cr.run_id}"
    print(head)
    if cr.error:
        print(_red(f"       error: {cr.error}"))
    for r in cr.assertion_results:
        mark = _green("✓") if r.passed else _red("✗")
        line = f"       {mark} {r.kind:<16} {r.detail}"
        print(line)
        if r.rationale:
            print(_dim(f"            ↳ {r.rationale}"))


def print_summary(suite: SuiteResult) -> None:
    bar = "=" * 60
    print(bar)
    color = _green if suite.failed == 0 else _red
    print(color(f"  {suite.passed}/{suite.total} cases passed, {suite.failed} failed"))
    print(bar)


def results_dir(root: Optional[Path] = None) -> Path:
    if root is not None:
        return root
    return Path(__file__).resolve().parent / "results"


def write_results_jsonl(suite: SuiteResult, root: Optional[Path] = None) -> Path:
    """Append one JSONL line per case to results/<timestamp>.jsonl."""
    base = results_dir(root)
    base.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = base / f"{ts}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for cr in suite.cases:
            f.write(json.dumps(cr.to_dict(), default=str, ensure_ascii=False) + "\n")
    return out
