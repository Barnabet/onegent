"""
Tool registry — the single source of truth for callable tools.

Tools register themselves at import time via the @tool decorator.
The registry exposes:
  - registration metadata (name, card, classification, owner, tags)
  - the pydantic schema (for LLM tool-call parameters)
  - the loaded card markdown (for the LLM tool-call description)
  - a `call(name, args, ctx)` entry point that validates + executes

Tools never raise to the caller — they return a `ToolResult` envelope.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, ValidationError


Classification = Literal["public", "internal", "confidential", "restricted"]
_CLASSIFICATION_ORDER = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}


# ---------------------------------------------------------------------------
# Public types used by tool authors and the framework
# ---------------------------------------------------------------------------


class ToolError(BaseModel):
    code: str
    message: str
    retriable: bool = False


class Citation(BaseModel):
    source: str
    url: Optional[str] = None
    detail: Optional[str] = None


class ToolResult(BaseModel):
    ok: bool
    data: Optional[dict] = None
    error: Optional[ToolError] = None
    warnings: List[str] = []
    citations: List[Citation] = []


@dataclass
class ToolCtx:
    """Per-call context passed to every tool. Tools must respect it."""

    run_id: str
    user_id: str
    pack_name: str
    classification_ceiling: Classification
    allowed_data_sources: List[str] = field(default_factory=list)
    # The audit logger is attached by the worker; tools may emit structured
    # events via ctx.audit(event_type, **fields).
    audit: Optional[Callable[..., None]] = None
    # Orchestrator-only fields. Populated by the worker when the running pack
    # is a router; ignored otherwise. The subagent.run tool reads them.
    allowed_packs: Optional[List[str]] = None
    emit: Optional[Callable[[dict], None]] = None


# ---------------------------------------------------------------------------
# Internal registry entry
# ---------------------------------------------------------------------------


@dataclass
class RegisteredTool:
    name: str
    fn: Callable[..., ToolResult]
    schema: Type[BaseModel]
    card_path: Path
    card_body: str
    classification: Classification
    owner: str
    tags: List[str]
    version: int

    def json_schema(self) -> dict:
        """Return the JSON schema for the tool's parameters (pydantic v2)."""
        return self.schema.model_json_schema()


_REGISTRY: Dict[str, RegisteredTool] = {}


# ---------------------------------------------------------------------------
# The @tool decorator
# ---------------------------------------------------------------------------


def tool(
    *,
    name: str,
    card: str,
    schema: Type[BaseModel],
    classification: Classification,
    owner: str,
    tags: Optional[List[str]] = None,
    version: int = 1,
) -> Callable[[Callable[..., ToolResult]], Callable[..., ToolResult]]:
    """
    Register a tool. The decorated function must accept (params, ctx) and
    return a ToolResult.

    `card` is a path relative to the module file that contains the @tool call.
    """

    def decorate(fn: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
        module = inspect.getmodule(fn)
        if module is None or not getattr(module, "__file__", None):
            raise RuntimeError(f"Cannot determine module path for tool {name}")
        module_dir = Path(module.__file__).resolve().parent
        card_path = (module_dir / card).resolve()
        if not card_path.is_file():
            raise FileNotFoundError(
                f"Tool {name!r}: card not found at {card_path}"
            )
        card_body = card_path.read_text(encoding="utf-8")

        _validate_card(name, card_body, card_path)

        if name in _REGISTRY:
            raise RuntimeError(f"Tool {name!r} already registered")

        _REGISTRY[name] = RegisteredTool(
            name=name,
            fn=fn,
            schema=schema,
            card_path=card_path,
            card_body=card_body,
            classification=classification,
            owner=owner,
            tags=tags or [],
            version=version,
        )
        return fn

    return decorate


# ---------------------------------------------------------------------------
# Card validation (lightweight — full lint in scripts/check_catalog.py)
# ---------------------------------------------------------------------------


_REQUIRED_CARD_SECTIONS = (
    "## Purpose",
    "## When to use",
    "## When NOT to use",
    "## Parameters",
    "## Returns",
    "## Errors",
    "## Examples",
)


def _validate_card(name: str, body: str, path: Path) -> None:
    missing = [s for s in _REQUIRED_CARD_SECTIONS if s not in body]
    if missing:
        raise ValueError(
            f"Tool {name!r}: card at {path} is missing required sections: {missing}"
        )
    # Frontmatter sanity: the `tool:` field must match the registered name.
    if not body.startswith("---"):
        raise ValueError(f"Tool {name!r}: card at {path} has no frontmatter")
    end = body.find("\n---", 3)
    if end == -1:
        raise ValueError(f"Tool {name!r}: card at {path} frontmatter not closed")
    front = body[3:end]
    # naive parse — full YAML is overkill here, we only check one field
    for line in front.splitlines():
        line = line.strip()
        if line.startswith("tool:"):
            declared = line.split(":", 1)[1].strip()
            if declared != name:
                raise ValueError(
                    f"Tool {name!r}: card frontmatter declares tool: {declared!r}"
                )
            break
    else:
        raise ValueError(f"Tool {name!r}: card frontmatter missing `tool:` field")


# ---------------------------------------------------------------------------
# Lookup + execution
# ---------------------------------------------------------------------------


def get(name: str) -> RegisteredTool:
    if name not in _REGISTRY:
        raise KeyError(f"Tool {name!r} is not registered")
    return _REGISTRY[name]


def has(name: str) -> bool:
    return name in _REGISTRY


def all_tools() -> List[RegisteredTool]:
    return list(_REGISTRY.values())


def reset_for_tests() -> None:
    """Test-only: clear the registry. Do not call in production code."""
    _REGISTRY.clear()


def classification_at_or_below(value: Classification, ceiling: Classification) -> bool:
    return _CLASSIFICATION_ORDER[value] <= _CLASSIFICATION_ORDER[ceiling]


def call(name: str, args: dict, ctx: ToolCtx) -> ToolResult:
    """Validate args, enforce classification ceiling, execute the tool."""
    entry = get(name)

    if not classification_at_or_below(entry.classification, ctx.classification_ceiling):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="classification_violation",
                message=(
                    f"Tool {name!r} classification {entry.classification} exceeds "
                    f"pack ceiling {ctx.classification_ceiling}"
                ),
                retriable=False,
            ),
        )

    try:
        params = entry.schema.model_validate(args)
    except ValidationError as e:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_input",
                message=f"Parameter validation failed: {e.errors(include_url=False)}",
                retriable=False,
            ),
        )

    try:
        result = entry.fn(params, ctx)
    except Exception as e:  # tools should never raise — capture and return
        result = ToolResult(
            ok=False,
            error=ToolError(
                code="tool_crashed",
                message=f"{type(e).__name__}: {e}",
                retriable=False,
            ),
        )

    return result


# ---------------------------------------------------------------------------
# Auto-discovery: import every `tools/*/` package so @tool runs
# ---------------------------------------------------------------------------


def discover(tools_root: Optional[Path] = None) -> None:
    """Import every tools/<domain>/ package, triggering @tool registrations."""
    import importlib

    if tools_root is None:
        tools_root = Path(__file__).resolve().parent.parent / "tools"
    if not tools_root.is_dir():
        return
    for child in sorted(tools_root.iterdir()):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        if not (child / "__init__.py").is_file():
            continue
        importlib.import_module(f"tools.{child.name}")
