"""Tool registrations for the `pptx` domain."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


# ---------------------------------------------------------------------------
# Param models
# ---------------------------------------------------------------------------


class ReadParams(BaseModel):
    path: str = Field(..., description="Path to a .pptx file.")


class ExtractTextParams(BaseModel):
    path: str = Field(..., description="Path to a .pptx file.")
    slides: Optional[str] = Field(
        None,
        description="1-based slide spec, e.g. '1', '1-3', '1,3-5,8'. Omit for every slide.",
    )
    include_notes: bool = Field(
        True,
        description="If true, also return the speaker notes for each slide.",
    )


class ExtractNotesParams(BaseModel):
    path: str = Field(..., description="Path to a .pptx file.")
    slides: Optional[str] = Field(
        None,
        description="1-based slide spec; omit for every slide.",
    )


class MergeParams(BaseModel):
    inputs: List[str] = Field(
        ...,
        description="List of input .pptx paths, in the order they should be concatenated. At least 2.",
    )
    output: str = Field(..., description="Path where the merged .pptx will be written.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class SplitParams(BaseModel):
    path: str = Field(..., description="Path to the source .pptx file.")
    slides: str = Field(
        ...,
        description="1-based slide spec to keep, e.g. '1-5' or '1,3,7-9'. Order is preserved.",
    )
    output: str = Field(..., description="Destination .pptx path for the extracted slides.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class ConvertParams(BaseModel):
    path: str = Field(..., description="Path to a .pptx file.")
    output: str = Field(..., description="Destination .pdf path (must end in .pdf).")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")
    timeout_seconds: int = Field(120, description="Hard limit on the LibreOffice subprocess.")


class SeeParams(BaseModel):
    path: str = Field(..., description="Path to a .pptx file.")
    slides: Optional[str] = Field(
        None,
        description="1-based slide spec; max 5 slides per call, e.g. '1', '2-4', '1,3,5'. Omit to render slide 1 only.",
    )
    scale: float = Field(
        2.0,
        description="Render scale; 2.0 ≈ 200dpi. Keep ≤ 3.0 to stay within model image limits.",
    )
    timeout_seconds: int = Field(120, description="Hard limit on the LibreOffice subprocess used to rasterise.")


class CreateParams(BaseModel):
    output: str = Field(
        ...,
        description="Destination .pptx path. Must end in `.pptx`. Parent dirs are created.",
    )
    slides: List[Dict[str, Any]] = Field(
        ...,
        description=(
            "Ordered list of slide objects. Each has a `type` field. Supported "
            "types: cover, title, section, content, two_column, kpi, table, "
            "chart, image, image_text, quote, conclusion. Any slide may also "
            "include a `notes` string for speaker notes."
        ),
    )
    theme: Union[str, Dict[str, str]] = Field(
        "professional",
        description=(
            "Theme name (default, professional, modern, minimal, vibrant, dark, "
            "midnight_executive, forest_moss, terracotta) or a custom object with "
            "`primary`/`secondary`/`accent`/`text`/`muted`/`surface`/`background`/"
            "`on_primary` hex colours and optional `header_font`/`body_font`."
        ),
    )
    layout: str = Field(
        "16x9",
        description="Slide size: '16x9' (default, 13.333x7.5in), '16x10', '4x3', or 'wide'.",
    )
    title: Optional[str] = Field(None, description="Deck metadata: document title.")
    author: Optional[str] = Field(None, description="Deck metadata: author.")
    subject: Optional[str] = Field(None, description="Deck metadata: subject.")
    page_numbers: bool = Field(
        False,
        description="If true, draw `N / total` in the bottom-right of every slide (skipped on the cover).",
    )
    overwrite: bool = Field(
        False,
        description="If true, replace the output file if it already exists.",
    )


class FromHtmlParams(BaseModel):
    """Inputs for `pptx.from_html` — render a complete HTML document to
    a picture-per-slide PPTX. One PDF page (from WeasyPrint) = one
    slide. The output is **not editable** in PowerPoint (each slide is
    a single Picture shape); the trade is pixel-perfect design
    fidelity. Use `pptx.create` if the user needs to edit the deck."""

    output: str = Field(
        ...,
        description="Destination .pptx path. Must end in `.pptx`. Parent dirs are created.",
    )
    html: str = Field(
        ...,
        description=(
            "Either (a) a complete HTML document as a string — must "
            "begin with `<!doctype html>` and include an `<html>` "
            "element with a `<head>`; declare ONE `@page` rule per "
            "deck (its size becomes the slide size, so e.g. `@page "
            "{ size: 13.333in 7.5in; margin: 0 }` for 16:9); or "
            "(b) the absolute path to a `.html`/`.htm` file on disk. "
            "Same input convention as `pdf.create`. Each rendered "
            "page in the resulting PDF becomes one slide."
        ),
    )
    notes: Optional[List[Optional[str]]] = Field(
        None,
        description=(
            "Optional speaker notes, one per slide in slide order. "
            "Pass `null` (or omit the index) for slides you don't want "
            "notes on. Length may be ≤ slide_count; extra slides get "
            "no notes."
        ),
    )
    image_dpi: int = Field(
        192,
        description=(
            "Rasterisation DPI (36–600). 192 is a good default — "
            "looks crisp on Retina displays and on a 1080p projector "
            "without bloating the .pptx. Bump to 300+ for print-quality "
            "decks; drop to 96 for tiny preview decks."
        ),
    )
    image_format: str = Field(
        "png",
        description=(
            "Image codec for each slide: `png` (default, lossless, "
            "supports transparency) or `jpeg` (smaller files on "
            "photo-heavy designs, no transparency)."
        ),
    )
    jpeg_quality: int = Field(
        88,
        description="JPEG quality 1–100 (only used when `image_format='jpeg'`).",
    )
    title: Optional[str] = Field(None, description="Deck metadata: document title.")
    author: Optional[str] = Field(None, description="Deck metadata: author.")
    subject: Optional[str] = Field(None, description="Deck metadata: subject.")
    engine: str = Field(
        "auto",
        description=(
            "Underlying HTML-to-PDF engine — same options as `pdf.create`: "
            "`auto` (default), `weasyprint`, or `libreoffice`. "
            "WeasyPrint is strongly preferred here too because slide "
            "dimensions come from the rendered `@page` size; "
            "LibreOffice silently drops `@page` rules and you'll end "
            "up with whatever default page it chooses."
        ),
    )
    timeout_seconds: int = Field(
        120,
        description="Hard limit on the LibreOffice subprocess (fallback path only).",
    )
    overwrite: bool = Field(
        False,
        description="If true, replace the output file if it already exists.",
    )


class FromHtmlEditableParams(BaseModel):
    """Inputs for `pptx.from_html_editable` — render an HTML document
    to a **fully editable** PPTX by scraping a headless Chromium's
    layout and rebuilding each slide with native python-pptx shapes
    (text boxes, rounded rectangles, tables, pictures). The output is
    presentation-grade *and* edit-grade; the trade-off vs. `pptx.from_html`
    is that exotic CSS features (filters, clip-path, complex masks)
    won't have native PPTX equivalents."""

    output: str = Field(
        ...,
        description="Destination .pptx path. Must end in `.pptx`. Parent dirs are created.",
    )
    html: str = Field(
        ...,
        description=(
            "Either (a) a complete HTML document as a string — must "
            "begin with `<!doctype html>` and include an `<html>` "
            "element with a `<head>`; or (b) the absolute path to a "
            "`.html`/`.htm` file on disk. Each `<section class=\"slide\">` "
            "(or any element with class `slide`) becomes one slide. "
            "Size each slide container to the deck size you want "
            "(e.g. `width: 13.333in; height: 7.5in` for 16:9)."
        ),
    )
    notes: Optional[List[Optional[str]]] = Field(
        None,
        description=(
            "Optional speaker notes, one per slide in slide order. "
            "Length ≤ slide_count; extra slides get no notes."
        ),
    )
    title: Optional[str] = Field(None, description="Deck metadata: document title.")
    author: Optional[str] = Field(None, description="Deck metadata: author.")
    subject: Optional[str] = Field(None, description="Deck metadata: subject.")
    timeout_seconds: int = Field(
        60,
        description="Hard limit on the Playwright extraction (page load + JS eval).",
    )
    overwrite: bool = Field(
        False,
        description="If true, replace the output file if it already exists.",
    )


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------


_OWNER = "team-doc-ai"


@tool(
    name="pptx.read",
    card="cards/read.md",
    schema=ReadParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "read", "metadata"],
)
def read(params: ReadParams, ctx: ToolCtx) -> ToolResult:
    return impl.read(params, ctx)


@tool(
    name="pptx.extract_text",
    card="cards/extract_text.md",
    schema=ExtractTextParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "read", "text"],
)
def extract_text(params: ExtractTextParams, ctx: ToolCtx) -> ToolResult:
    return impl.extract_text(params, ctx)


@tool(
    name="pptx.extract_notes",
    card="cards/extract_notes.md",
    schema=ExtractNotesParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "read", "notes"],
)
def extract_notes(params: ExtractNotesParams, ctx: ToolCtx) -> ToolResult:
    return impl.extract_notes(params, ctx)


@tool(
    name="pptx.merge",
    card="cards/merge.md",
    schema=MergeParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "write", "combine"],
)
def merge(params: MergeParams, ctx: ToolCtx) -> ToolResult:
    return impl.merge(params, ctx)


@tool(
    name="pptx.split",
    card="cards/split.md",
    schema=SplitParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "write", "split"],
)
def split(params: SplitParams, ctx: ToolCtx) -> ToolResult:
    return impl.split(params, ctx)


@tool(
    name="pptx.convert",
    card="cards/convert.md",
    schema=ConvertParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "write", "convert"],
)
def convert(params: ConvertParams, ctx: ToolCtx) -> ToolResult:
    return impl.convert(params, ctx)


@tool(
    name="pptx.see",
    card="cards/see.md",
    schema=SeeParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "read", "vision"],
)
def see(params: SeeParams, ctx: ToolCtx) -> ToolResult:
    return impl.see(params, ctx)


@tool(
    name="pptx.create",
    card="cards/create.md",
    schema=CreateParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "write", "create", "deck"],
)
def create(params: CreateParams, ctx: ToolCtx) -> ToolResult:
    return impl.create(params, ctx)


@tool(
    name="pptx.from_html",
    card="cards/from_html.md",
    schema=FromHtmlParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "write", "create", "deck", "html"],
)
def from_html(params: FromHtmlParams, ctx: ToolCtx) -> ToolResult:
    return impl.from_html(params, ctx)


@tool(
    name="pptx.from_html_editable",
    card="cards/from_html_editable.md",
    schema=FromHtmlEditableParams,
    classification="internal",
    owner=_OWNER,
    tags=["pptx", "write", "create", "deck", "html", "editable"],
)
def from_html_editable(params: FromHtmlEditableParams, ctx: ToolCtx) -> ToolResult:
    return impl.from_html_editable(params, ctx)
