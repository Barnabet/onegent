from runtime import tool_registry
from runtime.tool_registry import ToolCtx


def _ctx():
    return ToolCtx(
        run_id="t", user_id="u", pack_name="p",
        classification_ceiling="internal", allowed_data_sources=[],
    )


SAMPLE = """ACME ITALIA SPA
Revenue: EUR 412m (+8.2% YoY)
EBITDA: EUR 58m (margin 14.1%)
Net debt / EBITDA: 2.45x
A purely prose line with no signal.
"""


def test_extract_lines_finds_numeric():
    tool_registry.discover()
    r = tool_registry.call("text.extract_lines", {"text": SAMPLE}, _ctx())
    assert r.ok
    matched = {l["text"] for l in r.data["lines"]}
    assert any("Revenue" in t for t in matched)
    assert any("EBITDA: EUR 58m" in t for t in matched)


def test_extract_lines_filters_by_kind():
    tool_registry.discover()
    r = tool_registry.call(
        "text.extract_lines",
        {"text": SAMPLE, "kinds": ["percentage"]},
        _ctx(),
    )
    assert r.ok
    for line in r.data["lines"]:
        assert "percentage" in line["kinds"]


def test_extract_lines_empty():
    tool_registry.discover()
    r = tool_registry.call("text.extract_lines", {"text": "   "}, _ctx())
    assert not r.ok
    assert r.error.code == "empty_input"


def test_word_count():
    tool_registry.discover()
    r = tool_registry.call("text.word_count", {"text": "hello world"}, _ctx())
    assert r.ok
    assert r.data["words"] == 2
