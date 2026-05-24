"""
`xlsx` domain — read spreadsheet files (xlsx/xlsm + csv/tsv).

PR #3 ships `xlsx.read` only. Writers will follow as later PRs need them.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

from runtime.tool_registry import ToolCtx, ToolResult, ToolError


def read(params, ctx: ToolCtx) -> ToolResult:
    path = Path(params.path)
    if not path.is_file():
        return ToolResult(ok=False, error=ToolError(
            code="file_not_found", message=f"No file at {params.path!r}.", retriable=False,
        ))

    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        return _read_xlsx(path, params)
    if suffix in (".csv", ".tsv"):
        return _read_delimited(path, "\t" if suffix == ".tsv" else ",")
    return ToolResult(ok=False, error=ToolError(
        code="unsupported_format",
        message=f"Unsupported extension {suffix!r}. Supported: .xlsx, .xlsm, .csv, .tsv.",
        retriable=False,
    ))


def _read_xlsx(path: Path, params) -> ToolResult:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return ToolResult(ok=False, error=ToolError(
            code="dependency_missing", message="openpyxl is not installed.", retriable=False,
        ))

    try:
        wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    except Exception as e:
        return ToolResult(ok=False, error=ToolError(
            code="unsupported_format", message=f"Failed to open as xlsx: {e}", retriable=False,
        ))

    sheet_name = params.sheet or wb.sheetnames[0]
    if sheet_name not in wb.sheetnames:
        return ToolResult(ok=False, error=ToolError(
            code="sheet_not_found",
            message=f"Sheet {sheet_name!r} not in workbook. Available: {wb.sheetnames}.",
            retriable=False,
        ))
    ws = wb[sheet_name]

    rows: List[List] = []
    for row in ws.iter_rows(values_only=True):
        rows.append(list(row))

    headers: Optional[List] = None
    data_rows = rows
    if params.has_header and rows:
        headers = rows[0]
        data_rows = rows[1:]

    return ToolResult(ok=True, data={
        "sheet": sheet_name,
        "headers": headers,
        "rows": data_rows,
        "row_count": len(data_rows),
    })


def _read_delimited(path: Path, delimiter: str) -> ToolResult:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        rows = [row for row in reader]
    headers = rows[0] if rows else None
    data_rows = rows[1:] if rows else []
    return ToolResult(ok=True, data={
        "sheet": path.stem,
        "headers": headers,
        "rows": data_rows,
        "row_count": len(data_rows),
    })
