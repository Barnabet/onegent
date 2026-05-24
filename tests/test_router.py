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


def _ctx(allowed_packs, files=None):
    return ToolCtx(
        run_id="t",
        user_id="u",
        pack_name="router",
        classification_ceiling="internal",
        allowed_data_sources=["user_attachments"],
        allowed_packs=allowed_packs,
        emit=lambda ev: None,
        files=files,
    )


def test_router_pack_loads_and_binds():
    tool_registry.discover(REPO / "tools")
    from runtime.pack_loader import bind, load
    pack = load("router", root=REPO / "packs")
    bound = bind(pack, skills_root_path=REPO / "skills")
    assert [s.frontmatter.name for s in bound.skills] == [
        "router",
        "pdf_handling",
        "xlsx_handling",
    ]
    # Routing tools are always bound; file-read tools come from pdf_handling
    # and xlsx_handling so the router can do small read-only info-gathering.
    assert {"orchestrator.list_packs", "orchestrator.delegate"} <= set(bound.tools)
    assert "pdf.read" in bound.tools
    assert "xlsx.read" in bound.tools


def test_delegate_forwards_all_files_by_default():
    tool_registry.discover(REPO / "tools")
    from tools.orchestrator import impl

    captured = {}

    def fake_run(bound, message, child_ctx, emit):
        captured["files"] = child_ctx.files
        class _S:
            turns = 1
            tool_calls = 0
            final_finish_reason = "stop"
        return _S()

    files = [
        {"file_id": "f1", "name": "a.pdf", "path": "/tmp/a.pdf"},
        {"file_id": "f2", "name": "b.xlsx", "path": "/tmp/b.xlsx"},
    ]
    ctx = _ctx(["hello"], files=files)

    import orchestrator.subagent as sub
    orig = sub.run
    sub.run = fake_run
    try:
        from tools.orchestrator.registry import DelegateParams
        res = impl.delegate(DelegateParams(pack="hello", message="x"), ctx)
    finally:
        sub.run = orig

    assert res.ok
    assert captured["files"] == files


def test_delegate_filters_files_by_id():
    tool_registry.discover(REPO / "tools")
    from tools.orchestrator import impl

    captured = {}

    def fake_run(bound, message, child_ctx, emit):
        captured["files"] = child_ctx.files
        class _S:
            turns = 1
            tool_calls = 0
            final_finish_reason = "stop"
        return _S()

    files = [
        {"file_id": "f1", "name": "a.pdf", "path": "/tmp/a.pdf"},
        {"file_id": "f2", "name": "b.xlsx", "path": "/tmp/b.xlsx"},
    ]
    ctx = _ctx(["hello"], files=files)

    import orchestrator.subagent as sub
    orig = sub.run
    sub.run = fake_run
    try:
        from tools.orchestrator.registry import DelegateParams
        # Forward only f2.
        res = impl.delegate(
            DelegateParams(pack="hello", message="x", files=["f2", "unknown"]),
            ctx,
        )
    finally:
        sub.run = orig

    assert res.ok
    assert [f["file_id"] for f in captured["files"]] == ["f2"]


def test_delegate_empty_files_list_forwards_none():
    tool_registry.discover(REPO / "tools")
    from tools.orchestrator import impl

    captured = {}

    def fake_run(bound, message, child_ctx, emit):
        captured["files"] = child_ctx.files
        class _S:
            turns = 1
            tool_calls = 0
            final_finish_reason = "stop"
        return _S()

    files = [{"file_id": "f1", "name": "a.pdf", "path": "/tmp/a.pdf"}]
    ctx = _ctx(["hello"], files=files)

    import orchestrator.subagent as sub
    orig = sub.run
    sub.run = fake_run
    try:
        from tools.orchestrator.registry import DelegateParams
        res = impl.delegate(
            DelegateParams(pack="hello", message="x", files=[]),
            ctx,
        )
    finally:
        sub.run = orig

    assert res.ok
    assert captured["files"] == []


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


# ---------------------------------------------------------------------------
# Skills allow-list + ad-hoc / extra_skills delegation
# ---------------------------------------------------------------------------


def _fake_run_capture(captured):
    def fake_run(bound, message, child_ctx, emit):
        captured["bound"] = bound
        captured["child_ctx"] = child_ctx
        captured["message"] = message
        class _S:
            turns = 1
            tool_calls = 0
            final_finish_reason = "stop"
        return _S()
    return fake_run


def test_list_skills_returns_full_catalog():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(allowed_packs=[])
    res = tool_registry.call("orchestrator.list_skills", {}, ctx)
    assert res.ok
    names = {s["name"] for s in res.data["skills"]}
    # Whatever skills exist on disk should be returned; sanity-check a few.
    assert {"router", "pdf_handling", "xlsx_handling"}.issubset(names)
    for entry in res.data["skills"]:
        assert entry["description"]


def test_list_skills_without_router_context_fails():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(allowed_packs=None)
    res = tool_registry.call("orchestrator.list_skills", {}, ctx)
    assert not res.ok
    assert res.error.code == "no_router_context"


def test_delegate_requires_pack_or_skills():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(allowed_packs=["hello"])
    res = tool_registry.call(
        "orchestrator.delegate", {"message": "x"}, ctx,
    )
    assert not res.ok
    assert res.error.code == "invalid_input"


def test_delegate_rejects_both_pack_and_skills():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(allowed_packs=["hello"])
    res = tool_registry.call(
        "orchestrator.delegate",
        {"pack": "hello", "skills": ["pdf_handling"], "message": "x"},
        ctx,
    )
    assert not res.ok
    assert res.error.code == "invalid_input"


def test_delegate_rejects_extra_skills_without_pack():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(allowed_packs=["hello"])
    res = tool_registry.call(
        "orchestrator.delegate",
        {"skills": ["pdf_handling"], "extra_skills": ["xlsx_handling"], "message": "x"},
        ctx,
    )
    assert not res.ok
    assert res.error.code == "invalid_input"


def test_delegate_skills_only_binds_ad_hoc_subagent():
    tool_registry.discover(REPO / "tools")
    from tools.orchestrator import impl
    from tools.orchestrator.registry import DelegateParams

    captured = {}
    ctx = _ctx(allowed_packs=["hello"])

    import orchestrator.subagent as sub
    orig = sub.run
    sub.run = _fake_run_capture(captured)
    try:
        res = impl.delegate(
            DelegateParams(skills=["pdf_handling"], message="inspect"),
            ctx,
        )
    finally:
        sub.run = orig

    assert res.ok
    # Sub-agent identity inherits the router's pack (model/classification/limits).
    assert captured["child_ctx"].pack_name == "router"
    # Only the requested skill is bound.
    bound_names = [s.frontmatter.name for s in captured["bound"].skills]
    assert bound_names == ["pdf_handling"]
    # The result reports the resolved skill list and a null pack.
    assert res.data["pack"] is None
    assert res.data["skills"] == ["pdf_handling"]
    # Specialists cannot themselves delegate.
    assert captured["child_ctx"].allowed_packs is None


def test_delegate_pack_plus_extra_skills_merges_dedup():
    tool_registry.discover(REPO / "tools")
    from tools.orchestrator import impl
    from tools.orchestrator.registry import DelegateParams

    captured = {}
    # router.yaml already includes pdf_handling — exercise the dedup path.
    ctx = _ctx(allowed_packs=["router"])

    import orchestrator.subagent as sub
    orig = sub.run
    sub.run = _fake_run_capture(captured)
    try:
        res = impl.delegate(
            DelegateParams(
                pack="router",
                extra_skills=["pdf_handling", "xlsx_handling"],  # pdf already in pack
                message="x",
            ),
            ctx,
        )
    finally:
        sub.run = orig

    assert res.ok
    bound_names = [s.frontmatter.name for s in captured["bound"].skills]
    # Pack skills come first, extras appended; duplicates dropped.
    assert bound_names == ["router", "pdf_handling", "xlsx_handling"]


def test_delegate_unknown_skill_fails_cleanly():
    tool_registry.discover(REPO / "tools")
    ctx = _ctx(allowed_packs=["hello"])
    res = tool_registry.call(
        "orchestrator.delegate",
        {"skills": ["does_not_exist"], "message": "x"},
        ctx,
    )
    assert not res.ok
    assert res.error.code in ("skill_not_found", "skills_bind_failed")
