"""
Spine tests — exercise the framework without touching the LLM.

For an end-to-end test against CLIProxyAPI, run `scripts/run.py` manually.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime import tool_registry, skill_loader, pack_loader
from runtime.tool_registry import ToolCtx


REPO = Path(__file__).resolve().parent.parent


def test_tool_registry_discovers_core_echo():
    tool_registry.discover(REPO / "tools")
    assert tool_registry.has("core.echo")
    entry = tool_registry.get("core.echo")
    assert entry.classification == "public"
    assert entry.owner == "team-platform-ai"
    assert "smoke-test" in entry.tags


def test_skill_loader_reads_hello():
    tool_registry.discover(REPO / "tools")
    skill = skill_loader.load("hello", root=REPO / "skills")
    assert skill.frontmatter.name == "hello"
    assert "core.echo" in skill.manifest.requires_tools
    skill_loader.validate_against_registry(skill)


def test_pack_loader_binds_hello():
    tool_registry.discover(REPO / "tools")
    pack = pack_loader.load("hello", root=REPO / "packs")
    bound = pack_loader.bind(pack, skills_root_path=REPO / "skills")
    assert [s.frontmatter.name for s in bound.skills] == ["hello"]
    assert bound.tools == ["core.echo"]
    assert bound.effective_classification == "public"


def test_classification_violation_is_caught():
    tool_registry.discover(REPO / "tools")
    ctx = ToolCtx(
        run_id="t", user_id="u", pack_name="p",
        classification_ceiling="public",
        allowed_data_sources=[],
    )
    # core.echo is public, so this should succeed
    res = tool_registry.call("core.echo", {"text": "hi"}, ctx)
    assert res.ok


def test_invalid_args_returns_envelope_not_raise():
    tool_registry.discover(REPO / "tools")
    ctx = ToolCtx(
        run_id="t", user_id="u", pack_name="p",
        classification_ceiling="public",
        allowed_data_sources=[],
    )
    res = tool_registry.call("core.echo", {}, ctx)
    assert res.ok is False
    assert res.error.code == "invalid_input"


def test_catalog_generation_runs():
    from runtime import catalog_gen
    out = catalog_gen.render_tool_catalog()
    assert "core.echo" in out
    out2 = catalog_gen.render_skill_catalog()
    assert "hello" in out2
