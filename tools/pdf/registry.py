"""Tool registrations for the `pdf` domain."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


# ---------------------------------------------------------------------------
# Param models
# ---------------------------------------------------------------------------


class ReadParams(BaseModel):
    path: str = Field(..., description="Path to a .pdf file.")
    password: Optional[str] = Field(None, description="Password if the PDF is encrypted.")


class ExtractTextParams(BaseModel):
    path: str = Field(..., description="Path to a .pdf file.")
    pages: Optional[str] = Field(
        None,
        description="1-based page spec, e.g. '1', '1-3', '1,3-5,8'. Omit for all pages.",
    )
    preserve_layout: bool = Field(
        False,
        description="If true, pdfplumber preserves visual layout (whitespace, columns).",
    )


class ExtractTablesParams(BaseModel):
    path: str = Field(..., description="Path to a .pdf file.")
    pages: Optional[str] = Field(None, description="1-based page spec; omit for all pages.")


class MergeParams(BaseModel):
    inputs: List[str] = Field(..., description="List of input .pdf paths, in the order they should be concatenated. At least 2.")
    output: str = Field(..., description="Path where the merged PDF will be written. Must end in .pdf.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class SplitParams(BaseModel):
    path: str = Field(..., description="Path to the source .pdf file.")
    pages: str = Field(..., description="1-based page spec to keep, e.g. '1-5' or '1,3,7-9'.")
    output: str = Field(..., description="Destination .pdf path for the extracted pages.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class RotateParams(BaseModel):
    path: str = Field(..., description="Path to the source .pdf file.")
    pages: Optional[str] = Field(None, description="1-based page spec to rotate; omit to rotate every page.")
    degrees: int = Field(..., description="Rotation amount: one of ±90, ±180, ±270.")
    output: str = Field(..., description="Destination .pdf path.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class EncryptParams(BaseModel):
    path: str = Field(..., description="Path to the source .pdf file.")
    user_password: str = Field(..., description="Password required to *open* the PDF.")
    owner_password: Optional[str] = Field(None, description="Password required to change permissions; defaults to user_password.")
    output: str = Field(..., description="Destination .pdf path.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class DecryptParams(BaseModel):
    path: str = Field(..., description="Path to the encrypted .pdf file.")
    password: str = Field(..., description="Password that opens the PDF.")
    output: str = Field(..., description="Destination .pdf path (will be written unencrypted).")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class OcrParams(BaseModel):
    path: str = Field(..., description="Path to the .pdf file to OCR.")
    pages: Optional[str] = Field(None, description="1-based page spec; omit for every page.")
    lang: str = Field("eng", description="Tesseract language code (e.g. 'eng', 'fra', 'deu', 'eng+fra').")
    scale: float = Field(2.0, description="Render scale before OCR. Higher = sharper but slower. 1.0 = native.")


class FormFieldsParams(BaseModel):
    path: str = Field(..., description="Path to the .pdf file to inspect.")


class FillFormParams(BaseModel):
    path: str = Field(..., description="Path to the source .pdf with fillable fields.")
    values: Dict[str, str] = Field(..., description="Mapping of field-name → value to write.")
    output: str = Field(..., description="Destination .pdf path.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")


class SeeParams(BaseModel):
    path: str = Field(..., description="Path to a .pdf file.")
    pages: Optional[str] = Field(
        None,
        description="1-based page spec, e.g. '1', '1-5', '2,4'. Max 5 pages per call. Omit for the first page only.",
    )
    scale: float = Field(2.0, description="Render scale; 2.0 ≈ ~200dpi. Keep ≤ 3.0 to stay within model image limits.")


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------


_OWNER = "team-doc-ai"


@tool(
    name="pdf.read",
    card="cards/read.md",
    schema=ReadParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "read", "metadata"],
)
def read(params: ReadParams, ctx: ToolCtx) -> ToolResult:
    return impl.read(params, ctx)


@tool(
    name="pdf.extract_text",
    card="cards/extract_text.md",
    schema=ExtractTextParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "read", "text"],
)
def extract_text(params: ExtractTextParams, ctx: ToolCtx) -> ToolResult:
    return impl.extract_text(params, ctx)


@tool(
    name="pdf.extract_tables",
    card="cards/extract_tables.md",
    schema=ExtractTablesParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "read", "tabular"],
)
def extract_tables(params: ExtractTablesParams, ctx: ToolCtx) -> ToolResult:
    return impl.extract_tables(params, ctx)


@tool(
    name="pdf.merge",
    card="cards/merge.md",
    schema=MergeParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "write", "combine"],
)
def merge(params: MergeParams, ctx: ToolCtx) -> ToolResult:
    return impl.merge(params, ctx)


@tool(
    name="pdf.split",
    card="cards/split.md",
    schema=SplitParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "write", "split"],
)
def split(params: SplitParams, ctx: ToolCtx) -> ToolResult:
    return impl.split(params, ctx)


@tool(
    name="pdf.rotate",
    card="cards/rotate.md",
    schema=RotateParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "write", "transform"],
)
def rotate(params: RotateParams, ctx: ToolCtx) -> ToolResult:
    return impl.rotate(params, ctx)


@tool(
    name="pdf.encrypt",
    card="cards/encrypt.md",
    schema=EncryptParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "write", "security"],
)
def encrypt(params: EncryptParams, ctx: ToolCtx) -> ToolResult:
    return impl.encrypt(params, ctx)


@tool(
    name="pdf.decrypt",
    card="cards/decrypt.md",
    schema=DecryptParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "write", "security"],
)
def decrypt(params: DecryptParams, ctx: ToolCtx) -> ToolResult:
    return impl.decrypt(params, ctx)


@tool(
    name="pdf.ocr",
    card="cards/ocr.md",
    schema=OcrParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "read", "ocr"],
)
def ocr(params: OcrParams, ctx: ToolCtx) -> ToolResult:
    return impl.ocr(params, ctx)


@tool(
    name="pdf.form_fields",
    card="cards/form_fields.md",
    schema=FormFieldsParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "read", "forms"],
)
def form_fields(params: FormFieldsParams, ctx: ToolCtx) -> ToolResult:
    return impl.form_fields(params, ctx)


@tool(
    name="pdf.fill_form",
    card="cards/fill_form.md",
    schema=FillFormParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "write", "forms"],
)
def fill_form(params: FillFormParams, ctx: ToolCtx) -> ToolResult:
    return impl.fill_form(params, ctx)


@tool(
    name="pdf.see",
    card="cards/see.md",
    schema=SeeParams,
    classification="internal",
    owner=_OWNER,
    tags=["pdf", "read", "vision"],
)
def see(params: SeeParams, ctx: ToolCtx) -> ToolResult:
    return impl.see(params, ctx)
