"""Tool registrations for the `html` domain."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


# ---------------------------------------------------------------------------
# Param models
# ---------------------------------------------------------------------------


class ReadParams(BaseModel):
    path: str = Field(..., description="Path to a `.html` or `.htm` file.")


class ExtractTextParams(BaseModel):
    path: str = Field(..., description="Path to a `.html` or `.htm` file.")
    max_chars: int = Field(
        50_000,
        description=(
            "Maximum characters to return. The result will be truncated and "
            "`truncated=true` set when the limit is hit. Pass 0 to disable."
        ),
    )


class ToPdfParams(BaseModel):
    path: str = Field(..., description="Path to a `.html` or `.htm` file.")
    output: str = Field(..., description="Destination `.pdf` path (must end in `.pdf`).")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")
    timeout_seconds: int = Field(120, description="Hard limit on the LibreOffice subprocess.")


class SeeParams(BaseModel):
    path: str = Field(..., description="Path to a `.html` or `.htm` file.")
    pages: Optional[str] = Field(
        None,
        description=(
            "1-based page spec; max 5 pages per call, e.g. '1', '2-4', '1,3,5'. "
            "Omit to render page 1 only. Pages refer to the print-pagination of "
            "the document (the same paginator that `@media print` uses)."
        ),
    )
    scale: float = Field(
        2.0,
        description="Render scale; 2.0 ≈ 200dpi. Keep ≤ 3.0 to stay within model image limits.",
    )
    timeout_seconds: int = Field(120, description="Hard limit on the LibreOffice subprocess used to rasterise.")


class CreateParams(BaseModel):
    output: str = Field(
        ...,
        description="Destination `.html` (or `.htm`) path. Parent dirs are created.",
    )
    elements: List[Dict[str, Any]] = Field(
        ...,
        description=(
            "Ordered list of element objects. Each has a `type` field. Supported "
            "types: cover, title, heading, paragraph, bullets, numbered, callout "
            "(variant: info/tip/note/success/warning/danger), quote, banner, "
            "kpi_row, card, columns, badges, table, chart (kind: bar/line/pie), "
            "timeline, hrule, spacer, image, raw_html, page_break, toc, "
            "details (collapsible). Inline markup in text fields: <b>, <i>, <u>, "
            "<code>, <br>, <a href='...'>; anything else is escaped."
        ),
    )
    title: Optional[str] = Field(
        None,
        description="Document <title> and the default report title metadata.",
    )
    theme: Union[str, Dict[str, str]] = Field(
        "professional",
        description=(
            "Theme name (default, professional, modern, minimal, vibrant, dark) "
            "or a custom palette object with hex colours: primary/secondary/"
            "accent/text/muted/surface/border/background/success/warning/danger/info."
        ),
    )
    header: Optional[Union[str, Dict[str, str]]] = Field(
        None,
        description=(
            "Optional page header. String for a centred line, or "
            "{left, center, right} for three slots. Hidden when printing."
        ),
    )
    footer: Optional[Union[str, Dict[str, str]]] = Field(
        None,
        description=(
            "Optional page footer. String or {left, center, right}. Hidden when printing."
        ),
    )
    max_width: int = Field(
        920,
        description="Max content width in pixels for the on-screen layout. Default 920.",
    )
    author: Optional[str] = Field(None, description="Document metadata: author.")
    subject: Optional[str] = Field(None, description="Document metadata: subject / description.")
    overwrite: bool = Field(
        False,
        description="If true, replace the output file if it already exists.",
    )


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------


_OWNER = "team-doc-ai"


@tool(
    name="html.read",
    card="cards/read.md",
    schema=ReadParams,
    classification="internal",
    owner=_OWNER,
    tags=["html", "read", "metadata"],
)
def read(params: ReadParams, ctx: ToolCtx) -> ToolResult:
    return impl.read(params, ctx)


@tool(
    name="html.extract_text",
    card="cards/extract_text.md",
    schema=ExtractTextParams,
    classification="internal",
    owner=_OWNER,
    tags=["html", "read", "text"],
)
def extract_text(params: ExtractTextParams, ctx: ToolCtx) -> ToolResult:
    return impl.extract_text(params, ctx)


@tool(
    name="html.to_pdf",
    card="cards/to_pdf.md",
    schema=ToPdfParams,
    classification="internal",
    owner=_OWNER,
    tags=["html", "write", "convert"],
)
def to_pdf(params: ToPdfParams, ctx: ToolCtx) -> ToolResult:
    return impl.to_pdf(params, ctx)


@tool(
    name="html.see",
    card="cards/see.md",
    schema=SeeParams,
    classification="internal",
    owner=_OWNER,
    tags=["html", "read", "vision"],
)
def see(params: SeeParams, ctx: ToolCtx) -> ToolResult:
    return impl.see(params, ctx)


@tool(
    name="html.create",
    card="cards/create.md",
    schema=CreateParams,
    classification="internal",
    owner=_OWNER,
    tags=["html", "write", "create", "report"],
)
def create(params: CreateParams, ctx: ToolCtx) -> ToolResult:
    return impl.create(params, ctx)
