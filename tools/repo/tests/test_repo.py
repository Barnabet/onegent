from runtime import tool_registry
from runtime.tool_registry import ToolCtx


def _ctx():
    return ToolCtx(
        run_id="t", user_id="u", pack_name="p",
        classification_ceiling="internal", allowed_data_sources=[],
    )


def test_read_doc_concepts():
    tool_registry.discover()
    r = tool_registry.call("repo.read_doc", {"path": "concepts.md"}, _ctx())
    assert r.ok
    assert "# Concepts" in r.data["content"]


def test_read_doc_escapes_blocked():
    tool_registry.discover()
    r = tool_registry.call("repo.read_doc", {"path": "../README.md"}, _ctx())
    assert not r.ok
    assert r.error.code == "path_outside_docs"


def test_read_catalog_lists_known_tool():
    tool_registry.discover()
    r = tool_registry.call("repo.read_catalog", {}, _ctx())
    assert r.ok
    names = {t["name"] for t in r.data["tools"]}
    assert "core.echo" in names
    assert "repo.read_catalog" in names


def test_search_catalog_finds_echo():
    tool_registry.discover()
    r = tool_registry.call("repo.search_catalog", {"query": "echo"}, _ctx())
    assert r.ok
    names = [h["name"] for h in r.data["hits"]]
    assert "core.echo" in names


def test_search_catalog_rejects_empty():
    tool_registry.discover()
    r = tool_registry.call("repo.search_catalog", {"query": "   "}, _ctx())
    assert not r.ok
    assert r.error.code == "empty_query"


def test_scaffold_tool_rejects_existing():
    tool_registry.discover()
    r = tool_registry.call(
        "repo.scaffold_tool",
        {"name": "core.echo", "owner": "team-platform-ai"},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "already_exists"


def test_scaffold_tool_rejects_bad_name():
    tool_registry.discover()
    r = tool_registry.call(
        "repo.scaffold_tool",
        {"name": "NoDots", "owner": "team-x"},
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "invalid_name"


def test_scaffold_skill_rejects_unknown_tool():
    tool_registry.discover()
    r = tool_registry.call(
        "repo.scaffold_skill",
        {
            "name": "this_will_never_exist_xyz",
            "owner": "team-x",
            "requires_tools": ["nonexistent.tool"],
            "classification": "internal",
        },
        _ctx(),
    )
    assert not r.ok
    assert r.error.code == "unknown_tools"
