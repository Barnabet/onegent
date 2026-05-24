"""
`text` domain — deterministic text utilities.

Per the authoring rule, tools never call the LLM. So `text.extract_lines`
returns structured extracts (numeric lines, header lines, key:value lines)
and lets the *skill* decide what to summarize and how. The skill is the
intelligent layer; the tool is the deterministic primitive.
"""

from __future__ import annotations

import re
from typing import List

from runtime.tool_registry import ToolCtx, ToolResult, ToolError


_NUMERIC_RE = re.compile(r"\b(\d{1,3}(?:[,.\s]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\b")
_PCT_RE = re.compile(r"\d+(?:\.\d+)?\s*%")
_CCY_RE = re.compile(r"\b(?:EUR|USD|GBP|CHF|JPY|CNY)\s?\d", re.IGNORECASE)
_KV_RE = re.compile(r"^\s*[A-Z][A-Za-z0-9 /\-]{1,60}:\s+\S")


def extract_lines(params, ctx: ToolCtx) -> ToolResult:
    text = params.text or ""
    if not text.strip():
        return ToolResult(ok=False, error=ToolError(
            code="empty_input", message="Input text is empty.", retriable=False,
        ))

    kinds = set(params.kinds or ["numeric", "key_value", "currency", "percentage"])
    out: List[dict] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        matched_kinds: List[str] = []
        if "numeric" in kinds and _NUMERIC_RE.search(stripped):
            matched_kinds.append("numeric")
        if "percentage" in kinds and _PCT_RE.search(stripped):
            matched_kinds.append("percentage")
        if "currency" in kinds and _CCY_RE.search(stripped):
            matched_kinds.append("currency")
        if "key_value" in kinds and _KV_RE.match(line):
            matched_kinds.append("key_value")
        if matched_kinds:
            out.append({"line_no": i, "text": stripped, "kinds": matched_kinds})

    return ToolResult(ok=True, data={"lines": out, "total_matched": len(out)})


def word_count(params, ctx: ToolCtx) -> ToolResult:
    text = params.text or ""
    words = re.findall(r"\w+", text)
    chars = len(text)
    return ToolResult(ok=True, data={"words": len(words), "chars": chars})
