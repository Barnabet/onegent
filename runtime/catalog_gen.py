"""
Generate docs/tool-catalog.md and docs/skill-catalog.md from the live
registry + skill folders. Used by `scripts/check_catalog.py`.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from runtime import tool_registry
from runtime import skill_loader


def render_tool_catalog() -> str:
    tool_registry.discover()
    tools = sorted(tool_registry.all_tools(), key=lambda t: t.name)
    by_domain: Dict[str, List[tool_registry.RegisteredTool]] = defaultdict(list)
    for t in tools:
        domain = t.name.split(".", 1)[0]
        by_domain[domain].append(t)

    by_tag: Dict[str, List[str]] = defaultdict(list)
    for t in tools:
        for tag in t.tags:
            by_tag[tag].append(t.name)

    lines: List[str] = []
    lines.append("# Tool catalog")
    lines.append("")
    lines.append("Generated from the live tool registry. Do not edit by hand.")
    lines.append("Re-render with `python scripts/check_catalog.py --write`.")
    lines.append("")
    lines.append(f"**{len(tools)} tools** across **{len(by_domain)} domains**.")
    lines.append("")

    lines.append("## By domain")
    lines.append("")
    for domain in sorted(by_domain):
        lines.append(f"### `{domain}`")
        lines.append("")
        for t in by_domain[domain]:
            lines.append(f"#### `{t.name}` &nbsp; <sub>v{t.version} · {t.classification} · owner: {t.owner}</sub>")
            lines.append("")
            lines.append("<details><summary>card</summary>")
            lines.append("")
            lines.append(t.card_body.strip())
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("## By tag")
    lines.append("")
    if not by_tag:
        lines.append("_(no tags yet)_")
    for tag in sorted(by_tag):
        names = ", ".join(f"`{n}`" for n in sorted(by_tag[tag]))
        lines.append(f"- **{tag}** — {names}")
    lines.append("")

    return "\n".join(lines)


def render_skill_catalog() -> str:
    catalog = skill_loader.catalog()
    lines: List[str] = []
    lines.append("# Skill catalog")
    lines.append("")
    lines.append("Generated from skills/*/SKILL.md frontmatter. Do not edit by hand.")
    lines.append("Re-render with `python scripts/check_catalog.py --write`.")
    lines.append("")
    lines.append(f"**{len(catalog)} skills.**")
    lines.append("")
    for entry in catalog:
        lines.append(f"## `{entry.name}` &nbsp; <sub>v{entry.version}</sub>")
        lines.append("")
        lines.append(entry.description)
        lines.append("")
    return "\n".join(lines)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent
