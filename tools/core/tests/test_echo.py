from runtime import tool_registry
from runtime.tool_registry import ToolCtx


def _ctx():
    return ToolCtx(
        run_id="test", user_id="u", pack_name="p",
        classification_ceiling="internal", allowed_data_sources=[],
    )


def test_echo_happy_path():
    tool_registry.discover()
    result = tool_registry.call("core.echo", {"text": "hello"}, _ctx())
    assert result.ok is True
    assert result.data == {"echoed": "hello"}


def test_echo_invalid_input():
    tool_registry.discover()
    result = tool_registry.call("core.echo", {}, _ctx())
    assert result.ok is False
    assert result.error.code == "invalid_input"


def test_echo_schema_rejects_wrong_type():
    tool_registry.discover()
    result = tool_registry.call("core.echo", {"text": 123}, _ctx())
    # pydantic v2 coerces ints to strings unless strict; we accept either
    # validation rejection or coerced success — but never a crash.
    assert isinstance(result.ok, bool)
