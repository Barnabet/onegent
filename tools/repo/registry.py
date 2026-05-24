"""Tool registrations for the `repo` domain — inspect docs/catalogs and scaffold new artifacts."""

from typing import List, Optional
from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


# ---------- read_doc ----------


class ReadDocParams(BaseModel):
    path: str = Field(..., description="Path under docs/, e.g. 'authoring-tools.md'.")


@tool(
    name="repo.read_doc",
    card="cards/read_doc.md",
    schema=ReadDocParams,
    classification="public",
    owner="team-platform-ai",
    tags=["docs", "read", "reference"],
)
def read_doc(params: ReadDocParams, ctx: ToolCtx) -> ToolResult:
    return impl.read_doc(params, ctx)


# ---------- read_catalog ----------


class ReadCatalogParams(BaseModel):
    pass


@tool(
    name="repo.read_catalog",
    card="cards/read_catalog.md",
    schema=ReadCatalogParams,
    classification="public",
    owner="team-platform-ai",
    tags=["catalog", "read", "reference"],
)
def read_catalog(params: ReadCatalogParams, ctx: ToolCtx) -> ToolResult:
    return impl.read_catalog(params, ctx)


# ---------- search_catalog ----------


class SearchCatalogParams(BaseModel):
    query: str = Field(..., description="Free-text query, e.g. 'read excel' or 'summarize'.")
    limit: int = Field(8, ge=1, le=50, description="Max hits to return.")


@tool(
    name="repo.search_catalog",
    card="cards/search_catalog.md",
    schema=SearchCatalogParams,
    classification="public",
    owner="team-platform-ai",
    tags=["catalog", "search", "dedup"],
)
def search_catalog(params: SearchCatalogParams, ctx: ToolCtx) -> ToolResult:
    return impl.search_catalog(params, ctx)


# ---------- scaffold_tool ----------


class ScaffoldToolParams(BaseModel):
    name: str = Field(..., description="Full tool name as <domain>.<verb>, lowercase + underscores.")
    owner: str = Field(..., description="Owning team, e.g. 'team-credit-ai'.")


@tool(
    name="repo.scaffold_tool",
    card="cards/scaffold_tool.md",
    schema=ScaffoldToolParams,
    classification="internal",
    owner="team-platform-ai",
    tags=["scaffold", "write", "tool-authoring"],
)
def scaffold_tool(params: ScaffoldToolParams, ctx: ToolCtx) -> ToolResult:
    return impl.scaffold_tool(params, ctx)


# ---------- scaffold_skill ----------


class ScaffoldSkillParams(BaseModel):
    name: str = Field(..., description="Skill name, lowercase + underscores.")
    owner: str = Field(..., description="Owning team.")
    requires_tools: List[str] = Field(..., description="Existing tool names the skill will call.")
    classification: str = Field("internal", description="public | internal | confidential | restricted.")
    data_sources: Optional[List[str]] = Field(None, description="Coarse data-source allow-list.")


@tool(
    name="repo.scaffold_skill",
    card="cards/scaffold_skill.md",
    schema=ScaffoldSkillParams,
    classification="internal",
    owner="team-platform-ai",
    tags=["scaffold", "write", "skill-authoring"],
)
def scaffold_skill(params: ScaffoldSkillParams, ctx: ToolCtx) -> ToolResult:
    return impl.scaffold_skill(params, ctx)


# ---------- scaffold_pack ----------


class ScaffoldPackParams(BaseModel):
    name: str = Field(..., description="Pack name, lowercase + underscores.")
    owner: str = Field(..., description="Owning team.")
    description: str = Field(..., description="One paragraph on the persona served.")
    skills: List[str] = Field(..., description="Existing skill names in the pack.")
    classification: str = Field("internal", description="public | internal | confidential | restricted.")
    model: str = Field("claude-sonnet-4-6", description="Pinned model id.")
    allowed_data_sources: Optional[List[str]] = Field(None, description="Coarse allow-list.")


@tool(
    name="repo.scaffold_pack",
    card="cards/scaffold_pack.md",
    schema=ScaffoldPackParams,
    classification="internal",
    owner="team-platform-ai",
    tags=["scaffold", "write", "pack-authoring"],
)
def scaffold_pack(params: ScaffoldPackParams, ctx: ToolCtx) -> ToolResult:
    return impl.scaffold_pack(params, ctx)
