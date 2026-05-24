"""
Eval case schema + loader. Cases are plain YAML.

Example:

  id: hello_smoke
  pack: hello
  description: Echo tool is called and its output is reflected.
  user_message: "Please echo the word 'hippopotamus'."
  timeout: 60
  assertions:
    - kind: tool_called
      name: core.echo
    - kind: contains
      text: hippopotamus
      case_sensitive: false
    - kind: judge
      criterion: |
        The reply must acknowledge that the echo tool was invoked and
        return the echoed word verbatim.
      threshold: 4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# --- Assertion dataclasses --------------------------------------------------


@dataclass
class ContainsAssertion:
    text: str
    case_sensitive: bool = False
    kind: str = "contains"


@dataclass
class RegexAssertion:
    pattern: str
    flags: List[str] = field(default_factory=list)  # e.g. ["i", "m", "s"]
    kind: str = "regex"


@dataclass
class ToolCalledAssertion:
    name: str
    min_times: int = 1
    args_contains: Optional[Dict[str, Any]] = None
    kind: str = "tool_called"


@dataclass
class ToolNotCalledAssertion:
    name: str
    kind: str = "tool_not_called"


@dataclass
class JudgeAssertion:
    criterion: str
    threshold: int = 4  # 1..5
    kind: str = "judge"


@dataclass
class NoErrorAssertion:
    kind: str = "no_error"


Assertion = Any  # union of the above — kept loose for the runner switch


# --- Case -------------------------------------------------------------------


@dataclass
class EvalCase:
    id: str
    pack: str
    user_message: str
    description: str = ""
    timeout: float = 120.0
    assertions: List[Assertion] = field(default_factory=list)
    source_path: Optional[Path] = None


# --- Loader -----------------------------------------------------------------


_ASSERTION_BUILDERS = {
    "contains": lambda d: ContainsAssertion(
        text=d["text"], case_sensitive=bool(d.get("case_sensitive", False))
    ),
    "regex": lambda d: RegexAssertion(
        pattern=d["pattern"], flags=list(d.get("flags") or [])
    ),
    "tool_called": lambda d: ToolCalledAssertion(
        name=d["name"],
        min_times=int(d.get("min_times", 1)),
        args_contains=d.get("args_contains"),
    ),
    "tool_not_called": lambda d: ToolNotCalledAssertion(name=d["name"]),
    "judge": lambda d: JudgeAssertion(
        criterion=d["criterion"], threshold=int(d.get("threshold", 4))
    ),
    "no_error": lambda d: NoErrorAssertion(),
}


def _build_assertion(raw: dict) -> Assertion:
    if not isinstance(raw, dict) or "kind" not in raw:
        raise ValueError(f"Assertion missing `kind`: {raw!r}")
    kind = raw["kind"]
    builder = _ASSERTION_BUILDERS.get(kind)
    if builder is None:
        raise ValueError(
            f"Unknown assertion kind {kind!r}. "
            f"Valid kinds: {sorted(_ASSERTION_BUILDERS)}"
        )
    return builder(raw)


def parse_case(raw: dict, source_path: Optional[Path] = None) -> EvalCase:
    if not isinstance(raw, dict):
        raise ValueError(f"{source_path}: case is not a mapping")
    try:
        return EvalCase(
            id=raw["id"],
            pack=raw["pack"],
            user_message=raw["user_message"],
            description=(raw.get("description") or "").strip(),
            timeout=float(raw.get("timeout", 120.0)),
            assertions=[_build_assertion(a) for a in (raw.get("assertions") or [])],
            source_path=source_path,
        )
    except KeyError as e:
        raise ValueError(f"{source_path}: case missing required field {e}") from None


def load_case_file(path: Path) -> EvalCase:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return parse_case(raw, source_path=path)


def cases_root(root: Optional[Path] = None) -> Path:
    if root is not None:
        return root
    return Path(__file__).resolve().parent / "cases"


def discover_cases(
    root: Optional[Path] = None,
    pack: Optional[str] = None,
    case_id: Optional[str] = None,
) -> List[EvalCase]:
    """Find all .yaml cases under evals/cases/, optionally filtered."""
    base = cases_root(root)
    if not base.is_dir():
        return []
    found: List[EvalCase] = []
    for path in sorted(base.rglob("*.yaml")):
        case = load_case_file(path)
        if pack is not None and case.pack != pack:
            continue
        if case_id is not None and case.id != case_id:
            continue
        found.append(case)
    return found
