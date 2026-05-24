"""
LLM client — OpenAI-compatible HTTP, targeting local CLIProxyAPI today.

Single entry point: chat(messages, tools, model, system) -> ChatResponse.
Tool-call shape is normalised so the rest of the codebase never deals with
provider-specific quirks.

Configuration via env (with sensible defaults for local dev):
  LLM_BASE_URL  default: http://127.0.0.1:8317/v1
  LLM_API_KEY   default: your-api-key-1
  LLM_MODEL     default: claude-sonnet-4-6
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx


DEFAULT_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8317/v1")
DEFAULT_API_KEY = os.environ.get("LLM_API_KEY", "your-api-key-1")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")


@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    text: str
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    raw: Optional[dict] = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# Anthropic (and some other providers) restrict tool names to ^[a-zA-Z0-9_-]+$,
# so we cannot ship our `<domain>.<verb>` names directly. We translate
# `.` <-> `__` on the wire. The rest of the codebase deals only in dotted names.
_NAME_SEP_WIRE = "__"


def _wire_name(name: str) -> str:
    return name.replace(".", _NAME_SEP_WIRE)


def _dotted_name(wire: str) -> str:
    return wire.replace(_NAME_SEP_WIRE, ".")


def _tool_to_openai_schema(name: str, description: str, schema: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": _wire_name(name),
            "description": description,
            "parameters": schema,
        },
    }


def chat(
    messages: List[dict],
    tools: Optional[List[dict]] = None,
    model: Optional[str] = None,
    system: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 120.0,
) -> ChatResponse:
    """
    Send a chat completion request. `tools` is a list of dicts shaped as
    {"name": str, "description": str, "schema": dict}; we convert to OpenAI
    function-call format internally.
    """
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    key = api_key or DEFAULT_API_KEY
    mdl = model or DEFAULT_MODEL

    payload_messages: List[dict] = []
    if system:
        payload_messages.append({"role": "system", "content": system})
    payload_messages.extend(messages)

    payload: Dict[str, Any] = {"model": mdl, "messages": payload_messages}
    if tools:
        payload["tools"] = [
            _tool_to_openai_schema(t["name"], t["description"], t["schema"]) for t in tools
        ]
        payload["tool_choice"] = "auto"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{base}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()

    return _parse_response(body)


def _parse_response(body: dict) -> ChatResponse:
    choices = body.get("choices") or []
    if not choices:
        return ChatResponse(text="", finish_reason="empty", raw=body)
    choice = choices[0]
    msg = choice.get("message") or {}
    text = msg.get("content") or ""
    finish = choice.get("finish_reason") or "stop"

    raw_calls = msg.get("tool_calls") or []
    tool_calls: List[ToolCallRequest] = []
    for c in raw_calls:
        fn = c.get("function") or {}
        args_raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
        except json.JSONDecodeError:
            args = {"__raw__": args_raw}
        wire_name = fn.get("name", "")
        tool_calls.append(
            ToolCallRequest(
                id=c.get("id") or wire_name,
                name=_dotted_name(wire_name),
                arguments=args,
            )
        )

    return ChatResponse(text=text, tool_calls=tool_calls, finish_reason=finish, raw=body)


# ---------------------------------------------------------------------------
# Helpers used by the model loop to build follow-up messages
# ---------------------------------------------------------------------------


def assistant_message_from_response(resp: ChatResponse) -> dict:
    """Re-emit the assistant message so the next turn sees the same tool_calls."""
    msg: Dict[str, Any] = {"role": "assistant", "content": resp.text or None}
    if resp.tool_calls:
        msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": _wire_name(tc.name), "arguments": json.dumps(tc.arguments)},
            }
            for tc in resp.tool_calls
        ]
    return msg


def tool_result_message(call_id: str, content: str) -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": content}
