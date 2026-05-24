"""
Pack loader — parses packs/<name>.yaml and computes the effective tool set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from runtime.skill_loader import LoadedSkill, load as load_skill, validate_against_registry
from runtime.tool_registry import (
    Classification,
    _CLASSIFICATION_ORDER,
    classification_at_or_below,
    get as tool_get,
)


@dataclass
class PackLimits:
    max_tool_calls_per_run: int = 40
    max_tokens_per_run: int = 200000
    timeout_seconds: int = 300


@dataclass
class Pack:
    name: str
    version: str
    owner: str
    description: str
    skills: List[str]
    classification: Classification
    allowed_data_sources: List[str]
    model: str
    limits: PackLimits
    risk_review: Optional[dict] = None


@dataclass
class BoundPack:
    pack: Pack
    skills: List[LoadedSkill]
    tools: List[str]  # de-duplicated, in deterministic order

    @property
    def effective_classification(self) -> Classification:
        max_value: Classification = "public"
        for s in self.skills:
            if _CLASSIFICATION_ORDER[s.manifest.classification] > _CLASSIFICATION_ORDER[max_value]:
                max_value = s.manifest.classification
        for t in self.tools:
            entry = tool_get(t)
            if _CLASSIFICATION_ORDER[entry.classification] > _CLASSIFICATION_ORDER[max_value]:
                max_value = entry.classification
        return max_value


def packs_root(root: Optional[Path] = None) -> Path:
    if root is not None:
        return root
    return Path(__file__).resolve().parent.parent / "packs"


def _parse_pack(path: Path) -> Pack:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: pack file is not a mapping")
    limits_raw = raw.get("limits") or {}
    try:
        return Pack(
            name=raw["name"],
            version=str(raw.get("version", "0.0.0")),
            owner=raw["owner"],
            description=(raw.get("description") or "").strip(),
            skills=list(raw["skills"]),
            classification=raw.get("classification", "internal"),
            allowed_data_sources=list(raw.get("allowed_data_sources") or []),
            model=raw["model"],
            limits=PackLimits(
                max_tool_calls_per_run=int(limits_raw.get("max_tool_calls_per_run", 40)),
                max_tokens_per_run=int(limits_raw.get("max_tokens_per_run", 200000)),
                timeout_seconds=int(limits_raw.get("timeout_seconds", 300)),
            ),
            risk_review=raw.get("risk_review"),
        )
    except KeyError as e:
        raise ValueError(f"{path}: pack missing required field {e}") from None


def load(name: str, root: Optional[Path] = None) -> Pack:
    path = packs_root(root) / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Pack {name!r} not found at {path}")
    pack = _parse_pack(path)
    if pack.name != name:
        raise ValueError(f"Pack file {name}.yaml declares name {pack.name!r}")
    return pack


def bind(pack: Pack, skills_root_path: Optional[Path] = None) -> BoundPack:
    """Load all skills, validate against the registry, compute the tool union."""
    loaded: List[LoadedSkill] = []
    seen_tools: Dict[str, None] = {}  # ordered set

    for skill_name in pack.skills:
        skill = load_skill(skill_name, root=skills_root_path)
        validate_against_registry(skill)
        loaded.append(skill)
        for t in skill.manifest.requires_tools:
            seen_tools.setdefault(t, None)

    bound = BoundPack(pack=pack, skills=loaded, tools=list(seen_tools.keys()))

    if not classification_at_or_below(bound.effective_classification, pack.classification):
        raise ValueError(
            f"Pack {pack.name!r} declares classification {pack.classification} "
            f"but effective classification is {bound.effective_classification}"
        )

    if pack.classification in ("confidential", "restricted") and not pack.risk_review:
        raise ValueError(
            f"Pack {pack.name!r} at classification {pack.classification} requires a risk_review block"
        )

    return bound


def bind_skills(
    skill_names: List[str],
    identity: Pack,
    skills_root_path: Optional[Path] = None,
) -> BoundPack:
    """Bind an explicit list of skills under the given pack identity.

    Used by `orchestrator.delegate` for ad-hoc sub-agents (skills-only or
    pack + extra_skills) where `identity` carries the model / classification
    / limits to run under but the skill list is composed at delegate time.
    The identity's own `skills` field is ignored — only `skill_names` is bound.
    """
    pack = Pack(
        name=identity.name,
        version=identity.version,
        owner=identity.owner,
        description=identity.description,
        skills=list(skill_names),
        classification=identity.classification,
        allowed_data_sources=list(identity.allowed_data_sources),
        model=identity.model,
        limits=identity.limits,
        risk_review=identity.risk_review,
    )
    return bind(pack, skills_root_path=skills_root_path)
