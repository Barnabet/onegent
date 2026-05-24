"""
Implementations for the `repo` domain.

These tools let agents inspect the library's own docs and catalogs, and
scaffold new tools / skills / packs. Every write is sandboxed to known
subtrees; refuses overwrites and out-of-tree paths.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional

import yaml

from runtime.tool_registry import ToolCtx, ToolResult, ToolError, all_tools, discover
from runtime import skill_loader


def _repo_root() -> Path:
    # tools/repo/impl.py -> repo root is two parents up.
    return Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# read_doc — read a markdown file from docs/
# ---------------------------------------------------------------------------


def read_doc(params, ctx: ToolCtx) -> ToolResult:
    docs_root = _repo_root() / "docs"
    target = (docs_root / params.path).resolve()
    if docs_root not in target.parents and target != docs_root:
        return ToolResult(ok=False, error=ToolError(
            code="path_outside_docs", message="Path escapes docs/.", retriable=False,
        ))
    if not target.is_file():
        return ToolResult(ok=False, error=ToolError(
            code="not_found", message=f"Doc {params.path!r} not found.", retriable=False,
        ))
    return ToolResult(ok=True, data={
        "path": str(target.relative_to(_repo_root())),
        "content": target.read_text(encoding="utf-8"),
    })


# ---------------------------------------------------------------------------
# read_catalog — structured view of every tool + skill
# ---------------------------------------------------------------------------


def read_catalog(params, ctx: ToolCtx) -> ToolResult:
    discover()
    tools = [
        {
            "name": t.name,
            "version": t.version,
            "owner": t.owner,
            "classification": t.classification,
            "tags": t.tags,
            "domain": t.name.split(".", 1)[0],
            # First non-empty line after the heading is the Purpose line.
            "purpose": _extract_purpose(t.card_body),
        }
        for t in all_tools()
    ]
    skills = [
        {"name": s.name, "version": s.version, "description": s.description}
        for s in skill_loader.catalog()
    ]
    return ToolResult(ok=True, data={"tools": tools, "skills": skills})


def _extract_purpose(card_body: str) -> str:
    lines = card_body.splitlines()
    in_section = False
    for line in lines:
        if line.strip() == "## Purpose":
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            if line.strip():
                return line.strip()
    return ""


# ---------------------------------------------------------------------------
# search_catalog — dedup helper, by name/tag/free-text
# ---------------------------------------------------------------------------


def search_catalog(params, ctx: ToolCtx) -> ToolResult:
    discover()
    query = params.query.lower().strip()
    if not query:
        return ToolResult(ok=False, error=ToolError(
            code="empty_query", message="Query must be non-empty.", retriable=False,
        ))

    hits = []
    for t in all_tools():
        score = 0.0
        # exact name substring is the strongest signal
        if query in t.name.lower():
            score = max(score, 0.95)
        # tag exact match
        if any(query == tag.lower() for tag in t.tags):
            score = max(score, 0.9)
        # purpose / card fuzzy match
        purpose = _extract_purpose(t.card_body).lower()
        if purpose:
            ratio = SequenceMatcher(None, query, purpose).ratio()
            score = max(score, ratio * 0.8)
        # any tag substring
        for tag in t.tags:
            if query in tag.lower():
                score = max(score, 0.7)
        if score >= 0.3:
            hits.append({
                "name": t.name,
                "score": round(score, 3),
                "tags": t.tags,
                "purpose": _extract_purpose(t.card_body),
                "owner": t.owner,
            })
    hits.sort(key=lambda h: h["score"], reverse=True)
    return ToolResult(ok=True, data={"query": params.query, "hits": hits[: params.limit]})


# ---------------------------------------------------------------------------
# Scaffolding — tool / skill / pack
# ---------------------------------------------------------------------------


_VALID_NAME = "abcdefghijklmnopqrstuvwxyz0123456789_"
_VALID_DOMAIN_VERB = _VALID_NAME


def _validate_lower_ident(s: str, what: str) -> Optional[ToolError]:
    if not s or not all(c in _VALID_NAME for c in s):
        return ToolError(
            code="invalid_name",
            message=f"{what} must be lowercase letters, digits, and underscores; got {s!r}.",
            retriable=False,
        )
    return None


def scaffold_tool(params, ctx: ToolCtx) -> ToolResult:
    name = params.name.strip()
    if "." not in name:
        return ToolResult(ok=False, error=ToolError(
            code="invalid_name", message="Tool name must be <domain>.<verb>.", retriable=False,
        ))
    domain, verb = name.split(".", 1)
    for piece, label in [(domain, "domain"), (verb, "verb")]:
        err = _validate_lower_ident(piece, label)
        if err:
            return ToolResult(ok=False, error=err)

    discover()
    existing = {t.name for t in all_tools()}
    if name in existing:
        return ToolResult(ok=False, error=ToolError(
            code="already_exists", message=f"Tool {name!r} is already registered.", retriable=False,
        ))

    src = _repo_root() / "templates" / "tool"
    dst = _repo_root() / "tools" / domain
    card_path = dst / "cards" / f"{verb}.md"

    if card_path.exists():
        return ToolResult(ok=False, error=ToolError(
            code="already_exists", message=f"Card {card_path.relative_to(_repo_root())} already exists.",
            retriable=False,
        ))

    created: List[str] = []

    if not dst.exists():
        # First tool in this domain: copy the whole template tree.
        shutil.copytree(src, dst)
        # Then rewrite the template's example.do_thing -> domain.verb in the
        # files we just created. The template ships with one example tool.
        _rewrite_template(dst, name=name, domain=domain, verb=verb, owner=params.owner)
        created.append(str(dst.relative_to(_repo_root())))
    else:
        # Domain already exists — only add the new card and remind the user to
        # add a @tool registration to registry.py manually.
        card_path.parent.mkdir(parents=True, exist_ok=True)
        template_card = (src / "cards" / "do_thing.md").read_text(encoding="utf-8")
        card_path.write_text(
            template_card.replace("example.do_thing", name).replace("team-replace-me", params.owner),
            encoding="utf-8",
        )
        created.append(str(card_path.relative_to(_repo_root())))

    return ToolResult(
        ok=True,
        data={
            "tool": name,
            "created": created,
            "next_steps": [
                f"Implement {name} in {dst.relative_to(_repo_root())}/impl.py",
                f"Register it in {dst.relative_to(_repo_root())}/registry.py with @tool",
                f"Fill out the card at {card_path.relative_to(_repo_root())}",
                "Write tests covering happy path + each error code.",
                "Run: python scripts/check_catalog.py --write",
            ],
        },
    )


def _rewrite_template(dst: Path, *, name: str, domain: str, verb: str, owner: str) -> None:
    substitutions = {
        "example.do_thing": name,
        "team-replace-me": owner,
        "do_thing": verb,
        "ExampleParams": _camelize(verb) + "Params",
    }
    for path in dst.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".py", ".md", ".yaml", ".yml"):
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in substitutions.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
    # Rename the template card filename to match the verb.
    old_card = dst / "cards" / "do_thing.md"
    new_card = dst / "cards" / f"{verb}.md"
    if old_card.exists() and old_card != new_card:
        old_card.rename(new_card)
    # Rename the test file similarly.
    old_test = dst / "tests" / "test_do_thing.py"
    new_test = dst / "tests" / f"test_{verb}.py"
    if old_test.exists() and old_test != new_test:
        old_test.rename(new_test)


def _camelize(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def scaffold_skill(params, ctx: ToolCtx) -> ToolResult:
    name = params.name.strip()
    err = _validate_lower_ident(name, "skill name")
    if err:
        return ToolResult(ok=False, error=err)

    dst = _repo_root() / "skills" / name
    if dst.exists():
        return ToolResult(ok=False, error=ToolError(
            code="already_exists", message=f"Skill folder {dst.relative_to(_repo_root())} already exists.",
            retriable=False,
        ))

    discover()
    existing_tools = {t.name for t in all_tools()}
    missing = [t for t in params.requires_tools if t not in existing_tools]
    if missing:
        return ToolResult(ok=False, error=ToolError(
            code="unknown_tools",
            message=f"These tools are not registered: {missing}. Create them first.",
            retriable=False,
        ))

    src = _repo_root() / "templates" / "skill"
    shutil.copytree(src, dst)
    skill_md = dst / "SKILL.md"
    manifest = dst / "manifest.yaml"

    skill_md.write_text(
        skill_md.read_text(encoding="utf-8")
        .replace("<skill_name>", name)
        .replace("<Skill name>", name.replace("_", " ").title()),
        encoding="utf-8",
    )

    manifest_doc = {
        "name": name,
        "version": "0.1.0",
        "owner": params.owner,
        "requires_tools": params.requires_tools,
        "classification": params.classification,
        "data_sources": params.data_sources or [],
        "permissions": [],
    }
    manifest.write_text(yaml.safe_dump(manifest_doc, sort_keys=False), encoding="utf-8")

    return ToolResult(
        ok=True,
        data={
            "skill": name,
            "created": [str(dst.relative_to(_repo_root()))],
            "next_steps": [
                f"Write the workflow in {skill_md.relative_to(_repo_root())}.",
                "Add at least one eval under tests/evals/<skill>/.",
                "Run: python scripts/check_catalog.py --write",
            ],
        },
    )


def scaffold_pack(params, ctx: ToolCtx) -> ToolResult:
    name = params.name.strip()
    err = _validate_lower_ident(name, "pack name")
    if err:
        return ToolResult(ok=False, error=err)

    dst = _repo_root() / "packs" / f"{name}.yaml"
    if dst.exists():
        return ToolResult(ok=False, error=ToolError(
            code="already_exists", message=f"Pack {dst.relative_to(_repo_root())} already exists.",
            retriable=False,
        ))

    # Validate skills exist.
    skill_names = {s.name for s in skill_loader.catalog()}
    missing = [s for s in params.skills if s not in skill_names]
    if missing:
        return ToolResult(ok=False, error=ToolError(
            code="unknown_skills",
            message=f"These skills do not exist: {missing}.",
            retriable=False,
        ))

    pack_doc = {
        "name": name,
        "version": "0.1.0",
        "owner": params.owner,
        "description": params.description,
        "skills": params.skills,
        "classification": params.classification,
        "allowed_data_sources": params.allowed_data_sources or [],
        "model": params.model,
        "limits": {
            "max_tool_calls_per_run": 40,
            "max_tokens_per_run": 200000,
            "timeout_seconds": 300,
        },
    }
    dst.write_text(yaml.safe_dump(pack_doc, sort_keys=False), encoding="utf-8")
    return ToolResult(
        ok=True,
        data={
            "pack": name,
            "created": [str(dst.relative_to(_repo_root()))],
            "next_steps": [
                f"If classification is confidential or above, add a risk_review block in {dst.relative_to(_repo_root())}.",
                "Add at least one integration eval under tests/evals/packs/<pack>/.",
            ],
        },
    )
