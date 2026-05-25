"""
Router / orchestrator tool tests. No LLM is touched — we call the
orchestrator.delegate tool directly with a hand-built ToolCtx, the same
way the model would. The pack + skill catalogs are inlined into the
router's system prompt natively, so there are no list_* tools to test.
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
        "pptx_handling",
        "html_reporting",
    ]
    # Routing tools are always bound; file-read tools come from pdf_handling,
    # xlsx_handling, pptx_handling, and html_reporting so the router can do
    # small read-only info-gathering on each attachment type and pick the
    # right output format.
    assert {"orchestrator.delegate"} <= set(bound.tools)
    # The retired list_* tools must NOT be bound.
    assert "orchestrator.list_packs" not in bound.tools
    assert "orchestrator.list_skills" not in bound.tools
    assert "pdf.read" in bound.tools
    assert "xlsx.read" in bound.tools
    assert "pptx.read" in bound.tools
    assert "html.create" in bound.tools


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


def test_list_tools_are_retired():
    """The router gets pack + skill catalogs natively in its system prompt,
    so the listing tools no longer exist in the registry."""
    tool_registry.discover(REPO / "tools")
    assert not tool_registry.has("orchestrator.list_packs")
    assert not tool_registry.has("orchestrator.list_skills")


def test_router_system_prompt_inlines_pack_and_skill_catalogs():
    from runtime.pack_loader import bind, load
    from orchestrator.subagent import build_system_prompt

    tool_registry.discover(REPO / "tools")
    pack = load("router", root=REPO / "packs")
    bound = bind(pack, skills_root_path=REPO / "skills")
    prompt = build_system_prompt(
        bound,
        files=None,
        allowed_packs=["hello", "credit_analyst"],
    )
    # Pack catalog is present, with descriptions.
    assert "Delegatable packs (2)" in prompt
    assert "- hello" in prompt
    assert "- credit_analyst" in prompt
    # Skill catalog is present and includes the on-disk skills.
    assert "Composable skills" in prompt
    assert "- pdf_handling" in prompt
    assert "- xlsx_handling" in prompt


def test_non_router_run_does_not_inline_catalogs():
    from runtime.pack_loader import bind, load
    from orchestrator.subagent import build_system_prompt

    tool_registry.discover(REPO / "tools")
    pack = load("hello", root=REPO / "packs")
    bound = bind(pack, skills_root_path=REPO / "skills")
    prompt = build_system_prompt(bound, files=None, allowed_packs=None)
    assert "Delegatable packs" not in prompt
    assert "Composable skills" not in prompt


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
    assert bound_names == ["router", "pdf_handling", "xlsx_handling", "pptx_handling", "html_reporting"]


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
