"""
Skill loader — parses SKILL.md frontmatter + body and manifest.yaml.

Progressive disclosure:
  - `catalog()` reads only frontmatter for every skill (cheap).
  - `load(name)` reads the full SKILL.md body + manifest (medium cost).
  - references/*.md is NOT auto-loaded; the model fetches them on demand.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from runtime.tool_registry import (
    Classification,
    classification_at_or_below,
    has as tool_exists,
    get as tool_get,
)


@dataclass
class SkillManifest:
    name: str
    version: str
    owner: str
    requires_tools: List[str]
    classification: Classification
    data_sources: List[str]
    permissions: List[str]


@dataclass
class SkillFrontmatter:
    name: str
    description: str
    version: str


@dataclass
class LoadedSkill:
    frontmatter: SkillFrontmatter
    body: str
    manifest: SkillManifest
    folder: Path

    def reference(self, relative_path: str) -> str:
        """Read a reference file on demand. Used by the framework, not by users."""
        target = (self.folder / relative_path).resolve()
        if not target.is_file() or self.folder not in target.parents:
            raise FileNotFoundError(f"Reference {relative_path!r} not found in skill {self.frontmatter.name}")
        return target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str, source: Path) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError(f"{source}: SKILL.md missing frontmatter")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError(f"{source}: SKILL.md frontmatter not closed")
    front_raw = text[3:end]
    body = text[end + 4 :].lstrip("\n")
    front = yaml.safe_load(front_raw) or {}
    if not isinstance(front, dict):
        raise ValueError(f"{source}: frontmatter is not a mapping")
    return front, body


def _parse_manifest(path: Path) -> SkillManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: manifest is not a mapping")
    try:
        return SkillManifest(
            name=raw["name"],
            version=str(raw.get("version", "0.0.0")),
            owner=raw["owner"],
            requires_tools=list(raw.get("requires_tools") or []),
            classification=raw.get("classification", "internal"),
            data_sources=list(raw.get("data_sources") or []),
            permissions=list(raw.get("permissions") or []),
        )
    except KeyError as e:
        raise ValueError(f"{path}: manifest missing required field {e}") from None


def _parse_frontmatter(path: Path) -> tuple[SkillFrontmatter, str]:
    text = path.read_text(encoding="utf-8")
    front, body = _split_frontmatter(text, path)
    try:
        return (
            SkillFrontmatter(
                name=front["name"],
                description=front["description"].strip(),
                version=str(front.get("version", "0.0.0")),
            ),
            body,
        )
    except KeyError as e:
        raise ValueError(f"{path}: frontmatter missing required field {e}") from None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def skills_root(root: Optional[Path] = None) -> Path:
    if root is not None:
        return root
    return Path(__file__).resolve().parent.parent / "skills"


def catalog(root: Optional[Path] = None) -> List[SkillFrontmatter]:
    """Return frontmatter for every skill on disk. Cheap."""
    base = skills_root(root)
    entries: List[SkillFrontmatter] = []
    if not base.is_dir():
        return entries
    for child in sorted(base.iterdir()):
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        front, _ = _parse_frontmatter(skill_md)
        entries.append(front)
    return entries


def load(name: str, root: Optional[Path] = None) -> LoadedSkill:
    base = skills_root(root)
    folder = base / name
    skill_md = folder / "SKILL.md"
    manifest_yaml = folder / "manifest.yaml"
    if not skill_md.is_file():
        raise FileNotFoundError(f"Skill {name!r}: SKILL.md not found at {skill_md}")
    if not manifest_yaml.is_file():
        raise FileNotFoundError(f"Skill {name!r}: manifest.yaml not found at {manifest_yaml}")

    frontmatter, body = _parse_frontmatter(skill_md)
    manifest = _parse_manifest(manifest_yaml)

    if frontmatter.name != name:
        raise ValueError(
            f"Skill folder {name!r} contains SKILL.md with name {frontmatter.name!r}"
        )
    if manifest.name != name:
        raise ValueError(
            f"Skill folder {name!r} contains manifest.yaml with name {manifest.name!r}"
        )

    return LoadedSkill(frontmatter=frontmatter, body=body, manifest=manifest, folder=folder)


def validate_against_registry(skill: LoadedSkill) -> None:
    """Every tool in the manifest must exist and be at-or-below the skill's classification."""
    for tool_name in skill.manifest.requires_tools:
        if not tool_exists(tool_name):
            raise ValueError(
                f"Skill {skill.frontmatter.name!r} requires unknown tool {tool_name!r}"
            )
        entry = tool_get(tool_name)
        if not classification_at_or_below(entry.classification, skill.manifest.classification):
            raise ValueError(
                f"Skill {skill.frontmatter.name!r} (classification {skill.manifest.classification}) "
                f"cannot bind tool {tool_name!r} (classification {entry.classification})"
            )
