from runtime import tool_registry
from runtime.tool_registry import ToolCtx


def _ctx():
    return ToolCtx(
        run_id="t", user_id="u", pack_name="p",
        classification_ceiling="confidential", allowed_data_sources=[],
    )


def test_fetch_by_entity():
    tool_registry.discover()
    r = tool_registry.call("docstore.fetch", {"query": "Globex"}, _ctx())
    assert r.ok
    assert r.data["entity"] == "Globex Corporation SA"
    assert "Luxembourg" in r.data["body"]


def test_fetch_with_doc_type_filter():
    tool_registry.discover()
    r = tool_registry.call(
        "docstore.fetch",
        {"query": "Globex", "doc_type": "kyc_dossier"},
        _ctx(),
    )
    assert r.ok
    assert r.data["doc_type"] == "kyc_dossier"


def test_fetch_not_found():
    tool_registry.discover()
    r = tool_registry.call("docstore.fetch", {"query": "this-entity-does-not-exist"}, _ctx())
    assert not r.ok
    assert r.error.code == "not_found"
