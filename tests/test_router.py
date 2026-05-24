"""
Router / orchestrator tool tests. No LLM is touched — we call the
orchestrator.list_packs and orchestrator.delegate tools directly with a
hand-built ToolCtx, the same way the model would.
"""

from __future__ import annotations

from pathlib import Path

from runtime import tool_registry
from runtime.tool_registry import ToolCtx


REPO = Path(__file__).resolve().parent.parent


def _ctx(allowed_packs):
    return ToolCtx(
        run_id="t",
        user_id="u",
        pack_name="router",
        classification_ceiling="public",
        allowed_data_sources=[],
        allowed_packs=allowed_packs,
        emit=lambda ev: None,
    )


def test_router_pack_loads_and_binds():
    tool_registry.discover(REPO / "tools")
    from runtime.pack_loader import bind, load
    pack = load("router", root=REPO / "packs")
    bound = bind(pack, skills_root_path=REPO / "skills")
    assert [s.frontmatter.name for s in bound.skills] == ["router"]
    assert set(bound.tools) == {"orchestrator.list_packs", "orchestrator.delegate"}


def test_list_packs_returns_allowed_set():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(["hello", "credit_analyst"])
    res = tool_registry.call("orchestrator.list_packs", {}, ctx)
    assert res.ok
    names = [p["name"] for p in res.data["packs"]]
    assert names == ["hello", "credit_analyst"]
    # Each entry carries a description + classification.
    for entry in res.data["packs"]:
        assert entry["description"]
        assert entry["classification"] in ("public", "internal", "confidential", "restricted")


def test_list_packs_without_router_context_fails():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(None)  # not a router run
    res = tool_registry.call("orchestrator.list_packs", {}, ctx)
    assert not res.ok
    assert res.error.code == "no_router_context"


def test_delegate_blocks_pack_not_in_allow_list():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(["hello"])  # credit_analyst is NOT allowed
    res = tool_registry.call(
        "orchestrator.delegate",
        {"pack": "credit_analyst", "message": "x"},
        ctx,
    )
    assert not res.ok
    assert res.error.code == "pack_not_allowed"


def test_delegate_blocks_unknown_pack_even_if_in_allow_list():
    tool_registry.discover(REPO / "tools")
    # Pack name is in the allow-list but the YAML doesn't exist.
    ctx = _ctx(["does_not_exist"])
    res = tool_registry.call(
        "orchestrator.delegate",
        {"pack": "does_not_exist", "message": "x"},
        ctx,
    )
    assert not res.ok
    assert res.error.code in ("pack_not_found", "pack_load_failed")


def test_delegate_without_router_context_fails():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(None)
    res = tool_registry.call(
        "orchestrator.delegate",
        {"pack": "hello", "message": "x"},
        ctx,
    )
    assert not res.ok
    assert res.error.code == "no_router_context"
