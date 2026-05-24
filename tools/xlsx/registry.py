"""Tool registrations for the `xlsx` domain."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from runtime.tool_registry import tool, ToolCtx, ToolResult
from . import impl


_OWNER = "team-doc-ai"


# ---------------------------------------------------------------------------
# Param models
# ---------------------------------------------------------------------------


class ReadParams(BaseModel):
    path: str = Field(..., description="Path to .xlsx, .xlsm, .csv, or .tsv file.")
    sheet: Optional[str] = Field(None, description="Sheet name (xlsx only). Ignored when all_sheets=true. Defaults to the first sheet.")
    has_header: bool = Field(True, description="If true, treat the first row as column headers.")
    all_sheets: bool = Field(False, description="If true, return every sheet (xlsx only) as a list under `sheets`.")
    max_rows: int = Field(
        10,
        description=(
            "Cap on data rows returned per sheet. Default 10 — enough for a "
            "preview without flooding the model context. Raise it only when "
            "you genuinely need more rows; for full-table computation use "
            "xlsx.sql instead."
        ),
    )


class InfoParams(BaseModel):
    path: str = Field(..., description="Path to .xlsx, .xlsm, .csv, or .tsv file.")


class SqlInputSpec(BaseModel):
    path: str = Field(..., description="Path to a .xlsx/.xlsm/.csv/.tsv file to load as one or more tables.")
    alias: Optional[str] = Field(None, description="Override the table name. With xlsx multi-sheet files and no `sheet` filter, sheets are loaded as <alias>_<sheet>.")
    sheet: Optional[str] = Field(None, description="For .xlsx files, restrict to a single sheet.")


class SqlParams(BaseModel):
    inputs: List[Union[SqlInputSpec, str]] = Field(
        ...,
        description="Files to expose as SQL tables. Each entry is either a path string or {path, alias?, sheet?}.",
    )
    query: str = Field(
        ...,
        description="A single read-only SQL statement (SELECT / WITH / VALUES). Standard SQLite dialect.",
    )
    max_rows: int = Field(1000, description="Cap on returned rows. Default 1000; raise if you need more.")


class _SheetSpec(BaseModel):
    headers: Optional[List[Any]] = None
    rows: List[List[Any]] = []


class WriteParams(BaseModel):
    output: str = Field(..., description="Destination path; extension determines the format (.xlsx/.xlsm/.csv/.tsv).")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")

    # Either supply `sheets` (multi-sheet, xlsx only) ...
    sheets: Optional[Dict[str, _SheetSpec]] = Field(
        None,
        description="Mapping of sheet-name to {headers, rows}. Use this for multi-sheet workbooks. xlsx only.",
    )
    # ... or supply a single sheet directly.
    sheet_name: Optional[str] = Field(None, description="Name of the single sheet to create (default 'Sheet1'). Ignored when `sheets` is given.")
    headers: Optional[List[Any]] = Field(None, description="Header row for the single-sheet path.")
    rows: Optional[List[List[Any]]] = Field(None, description="Data rows for the single-sheet path.")


class _CellEdit(BaseModel):
    cell: str = Field(..., description="Target cell in A1 notation (e.g. 'B2').")
    value: Any = Field(None, description="Literal value, or a formula starting with '=' (e.g. '=SUM(A1:A10)').")


class EditCellsParams(BaseModel):
    path: str = Field(..., description="Source .xlsx/.xlsm to edit.")
    output: str = Field(..., description="Destination .xlsx/.xlsm path (input is never modified in place).")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")
    sheet: Optional[str] = Field(None, description="Sheet to edit; defaults to the first sheet.")
    cells: List[_CellEdit] = Field(..., description="List of {cell, value} edits. Strings starting with '=' are written as formulas.")


class FormatParams(BaseModel):
    path: str = Field(..., description="Source .xlsx/.xlsm to style.")
    output: str = Field(..., description="Destination .xlsx/.xlsm path.")
    overwrite: bool = Field(False, description="If true, replace the output file if it already exists.")
    sheet: Optional[str] = Field(None, description="Sheet whose cells to style; defaults to the first sheet.")
    range: str = Field(..., description="A1 range, e.g. 'A1', 'A1:C10', 'A:A'. Required.")

    font_name: Optional[str] = Field(None, description="Font family, e.g. 'Arial'.")
    font_size: Optional[float] = Field(None, description="Font size in points.")
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    font_color: Optional[str] = Field(None, description="ARGB or RGB hex, e.g. 'FF0000' for red.")
    fill_color: Optional[str] = Field(None, description="Solid fill colour as ARGB/RGB hex, e.g. 'FFFF00'.")
    align: Optional[str] = Field(None, description="Horizontal alignment: 'left' | 'center' | 'right'.")
    number_format: Optional[str] = Field(None, description="Excel number format, e.g. '$#,##0;($#,##0);-' or '0.0%'.")
    column_widths: Optional[Dict[str, float]] = Field(
        None,
        description="Optional {column_letter: width} map applied to the same sheet, e.g. {'A': 20, 'B': 12}.",
    )


class ConvertParams(BaseModel):
    path: str = Field(..., description="Source file (.xlsx/.xlsm/.csv/.tsv).")
    output: str = Field(..., description="Destination file or directory (for explode mode). Extension picks the target format.")
    overwrite: bool = Field(False, description="If true, replace existing output(s).")
    sheet: Optional[str] = Field(None, description="When converting xlsx → csv/tsv, the sheet to export (default: first).")
    explode_sheets: bool = Field(
        False,
        description="If true and source is multi-sheet xlsx, write one CSV per sheet inside `output` (treated as a directory).",
    )


class RecalcParams(BaseModel):
    path: str = Field(..., description="Path to an .xlsx/.xlsm containing formulas to recalculate.")
    output: Optional[str] = Field(
        None,
        description="Where to write the recalculated workbook. Omit to overwrite the input file in place.",
    )
    overwrite: bool = Field(False, description="If `output` is given and exists, allow replacing it.")
    timeout_seconds: int = Field(60, description="Hard timeout for the LibreOffice invocation.")


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------


@tool(
    name="xlsx.read",
    card="cards/read.md",
    schema=ReadParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "read", "tabular"],
    version=2,
)
def read(params: ReadParams, ctx: ToolCtx) -> ToolResult:
    return impl.read(params, ctx)


@tool(
    name="xlsx.info",
    card="cards/info.md",
    schema=InfoParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "read", "metadata"],
)
def info(params: InfoParams, ctx: ToolCtx) -> ToolResult:
    return impl.info(params, ctx)


@tool(
    name="xlsx.sql",
    card="cards/sql.md",
    schema=SqlParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "read", "query", "sql"],
)
def sql(params: SqlParams, ctx: ToolCtx) -> ToolResult:
    return impl.sql(params, ctx)


@tool(
    name="xlsx.write",
    card="cards/write.md",
    schema=WriteParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "write", "create"],
)
def write(params: WriteParams, ctx: ToolCtx) -> ToolResult:
    return impl.write(params, ctx)


@tool(
    name="xlsx.edit_cells",
    card="cards/edit_cells.md",
    schema=EditCellsParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "write", "edit", "formula"],
)
def edit_cells(params: EditCellsParams, ctx: ToolCtx) -> ToolResult:
    return impl.edit_cells(params, ctx)


@tool(
    name="xlsx.format",
    card="cards/format.md",
    schema=FormatParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "write", "format", "style"],
)
def format_(params: FormatParams, ctx: ToolCtx) -> ToolResult:
    return impl.format_(params, ctx)


@tool(
    name="xlsx.convert",
    card="cards/convert.md",
    schema=ConvertParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "write", "convert"],
)
def convert(params: ConvertParams, ctx: ToolCtx) -> ToolResult:
    return impl.convert(params, ctx)


@tool(
    name="xlsx.recalc",
    card="cards/recalc.md",
    schema=RecalcParams,
    classification="internal",
    owner=_OWNER,
    tags=["spreadsheet", "write", "formula", "recalc"],
)
def recalc(params: RecalcParams, ctx: ToolCtx) -> ToolResult:
    return impl.recalc(params, ctx)
