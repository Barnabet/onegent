"""Tests for the expanded xlsx tool surface.

Covers happy paths plus every documented error code for xlsx.info, xlsx.sql,
xlsx.write, xlsx.edit_cells, xlsx.format, xlsx.convert, and xlsx.recalc.
The recalc test is skipped when LibreOffice is not on PATH.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest

from runtime import tool_registry
from runtime.tool_registry import ToolCtx


def _ctx():
    return ToolCtx(
        run_id="t", user_id="u", pack_name="p",
        classification_ceiling="internal", allowed_data_sources=[],
    )


@pytest.fixture(autouse=True)
def _discover():
    tool_registry.discover()


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_csv(tmp_path: Path, name: str = "loans.csv", rows=None) -> Path:
    p = tmp_path / name
    rows = rows or [["id", "amount"], ["L1", 100], ["L2", 250], ["L3", 75]]
    with p.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    return p


def _make_xlsx(tmp_path: Path, name: str = "report.xlsx", *, sheets=None) -> Path:
    openpyxl = pytest.importorskip("openpyxl")
    p = tmp_path / name
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheets = sheets or {
        "Revenue": [["region", "net"], ["EMEA", 12], ["NA", 18], ["APAC", 9]],
        "Costs":   [["region", "spend"], ["EMEA", 5], ["NA", 7], ["APAC", 3]],
    }
    for sname, rows in sheets.items():
        ws = wb.create_sheet(title=sname)
        for r in rows:
            ws.append(r)
    wb.save(str(p))
    return p


# ---------------------------------------------------------------------------
# xlsx.info
# ---------------------------------------------------------------------------


def test_info_csv(tmp_path):
    p = _make_csv(tmp_path)
    r = tool_registry.call("xlsx.info", {"path": str(p)}, _ctx())
    assert r.ok
    assert r.data["sheet_count"] == 1
    assert r.data["sheets"][0]["row_count"] == 3
    assert r.data["sheets"][0]["headers_preview"] == ["id", "amount"]


def test_info_multi_sheet_xlsx(tmp_path):
    p = _make_xlsx(tmp_path)
    r = tool_registry.call("xlsx.info", {"path": str(p)}, _ctx())
    assert r.ok
    assert r.data["sheet_count"] == 2
    names = [s["name"] for s in r.data["sheets"]]
    assert names == ["Revenue", "Costs"]
    rev = next(s for s in r.data["sheets"] if s["name"] == "Revenue")
    assert rev["row_count"] == 3
    assert rev["headers_preview"] == ["region", "net"]


def test_info_file_not_found():
    r = tool_registry.call("xlsx.info", {"path": "/tmp/nope.xlsx"}, _ctx())
    assert not r.ok and r.error.code == "file_not_found"


def test_info_unsupported_format(tmp_path):
    p = tmp_path / "x.docx"
    p.write_text("x")
    r = tool_registry.call("xlsx.info", {"path": str(p)}, _ctx())
    assert not r.ok and r.error.code == "unsupported_format"


# ---------------------------------------------------------------------------
# xlsx.read — new behaviour (all_sheets, sheet_names echo)
# ---------------------------------------------------------------------------


def test_read_all_sheets(tmp_path):
    p = _make_xlsx(tmp_path)
    r = tool_registry.call("xlsx.read", {"path": str(p), "all_sheets": True}, _ctx())
    assert r.ok
    assert r.data["sheet_names"] == ["Revenue", "Costs"]
    assert len(r.data["sheets"]) == 2
    assert r.data["sheets"][0]["headers"] == ["region", "net"]


def test_read_specific_sheet_echoes_names(tmp_path):
    p = _make_xlsx(tmp_path)
    r = tool_registry.call("xlsx.read", {"path": str(p), "sheet": "Costs"}, _ctx())
    assert r.ok
    assert r.data["sheet"] == "Costs"
    assert r.data["sheet_names"] == ["Revenue", "Costs"]
    assert r.data["headers"] == ["region", "spend"]


# ---------------------------------------------------------------------------
# xlsx.sql
# ---------------------------------------------------------------------------


def test_sql_sum_on_csv(tmp_path):
    p = _make_csv(tmp_path)
    r = tool_registry.call(
        "xlsx.sql",
        {"inputs": [str(p)], "query": "SELECT SUM(amount) AS total FROM loans"},
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["columns"] == ["total"]
    assert r.data["rows"] == [[425]]


def test_sql_groupby_on_xlsx_sheet(tmp_path):
    p = _make_xlsx(tmp_path)
    r = tool_registry.call(
        "xlsx.sql",
        {
            "inputs": [{"path": str(p), "sheet": "Revenue", "alias": "rev"}],
            "query": "SELECT region, net FROM rev ORDER BY net DESC",
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["rows"][0] == ["NA", 18]


def test_sql_join_across_sheets(tmp_path):
    p = _make_xlsx(tmp_path)
    r = tool_registry.call(
        "xlsx.sql",
        {
            "inputs": [{"path": str(p)}],
            "query": (
                "SELECT r.region, r.net - c.spend AS profit "
                "FROM Revenue r JOIN Costs c ON r.region = c.region "
                "ORDER BY profit DESC"
            ),
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["rows"][0] == ["NA", 11]
    assert "Revenue" in r.data["tables"]
    assert "Costs" in r.data["tables"]


def test_sql_forbidden_statement(tmp_path):
    p = _make_csv(tmp_path)
    r = tool_registry.call(
        "xlsx.sql",
        {"inputs": [str(p)], "query": "DROP TABLE loans"},
        _ctx(),
    )
    assert not r.ok and r.error.code == "forbidden_statement"


def test_sql_invalid_input_empty_query(tmp_path):
    p = _make_csv(tmp_path)
    r = tool_registry.call("xlsx.sql", {"inputs": [str(p)], "query": "   "}, _ctx())
    assert not r.ok and r.error.code == "invalid_input"


def test_sql_invalid_input_multiple_statements(tmp_path):
    p = _make_csv(tmp_path)
    r = tool_registry.call(
        "xlsx.sql",
        {"inputs": [str(p)], "query": "SELECT 1; SELECT 2"},
        _ctx(),
    )
    assert not r.ok and r.error.code == "invalid_input"


def test_sql_error_bad_query(tmp_path):
    p = _make_csv(tmp_path)
    r = tool_registry.call(
        "xlsx.sql",
        {"inputs": [str(p)], "query": "SELECT * FROM does_not_exist"},
        _ctx(),
    )
    assert not r.ok and r.error.code == "sql_error"


def test_sql_sheet_not_found(tmp_path):
    p = _make_xlsx(tmp_path)
    r = tool_registry.call(
        "xlsx.sql",
        {"inputs": [{"path": str(p), "sheet": "Ghost"}], "query": "SELECT 1"},
        _ctx(),
    )
    assert not r.ok and r.error.code == "sheet_not_found"


def test_sql_max_rows_truncation(tmp_path):
    p = _make_csv(tmp_path, "big.csv", rows=[["i"]] + [[i] for i in range(100)])
    r = tool_registry.call(
        "xlsx.sql",
        {"inputs": [str(p)], "query": "SELECT i FROM big", "max_rows": 5},
        _ctx(),
    )
    assert r.ok
    assert r.data["truncated"] is True
    assert len(r.data["rows"]) == 5


# ---------------------------------------------------------------------------
# xlsx.write
# ---------------------------------------------------------------------------


def test_write_single_sheet_xlsx(tmp_path):
    out = tmp_path / "out.xlsx"
    r = tool_registry.call(
        "xlsx.write",
        {
            "output": str(out),
            "headers": ["id", "amount"],
            "rows": [["L1", 100], ["L2", 250]],
        },
        _ctx(),
    )
    assert r.ok and out.is_file()
    assert r.data["sheet_count"] == 1


def test_write_multi_sheet_xlsx(tmp_path):
    out = tmp_path / "multi.xlsx"
    r = tool_registry.call(
        "xlsx.write",
        {
            "output": str(out),
            "sheets": {
                "Q1": {"headers": ["x"], "rows": [[1], [2]]},
                "Q2": {"headers": ["x"], "rows": [[3]]},
            },
        },
        _ctx(),
    )
    assert r.ok
    assert r.data["sheet_names"] == ["Q1", "Q2"]
    # Verify by reading back
    rb = tool_registry.call("xlsx.info", {"path": str(out)}, _ctx())
    assert [s["name"] for s in rb.data["sheets"]] == ["Q1", "Q2"]


def test_write_csv(tmp_path):
    out = tmp_path / "out.csv"
    r = tool_registry.call(
        "xlsx.write",
        {"output": str(out), "headers": ["a"], "rows": [[1], [2]]},
        _ctx(),
    )
    assert r.ok
    assert out.read_text().strip().splitlines() == ["a", "1", "2"]


def test_write_output_exists(tmp_path):
    out = tmp_path / "out.csv"
    out.write_text("x")
    r = tool_registry.call(
        "xlsx.write",
        {"output": str(out), "headers": ["a"], "rows": [[1]]},
        _ctx(),
    )
    assert not r.ok and r.error.code == "output_exists"


def test_write_invalid_input(tmp_path):
    out = tmp_path / "out.xlsx"
    r = tool_registry.call("xlsx.write", {"output": str(out)}, _ctx())
    assert not r.ok and r.error.code == "invalid_input"


def test_write_csv_rejects_multi_sheet(tmp_path):
    out = tmp_path / "out.csv"
    r = tool_registry.call(
        "xlsx.write",
        {"output": str(out), "sheets": {
            "A": {"headers": ["x"], "rows": [[1]]},
            "B": {"headers": ["x"], "rows": [[2]]},
        }},
        _ctx(),
    )
    assert not r.ok and r.error.code == "invalid_input"


def test_write_unsupported_format(tmp_path):
    out = tmp_path / "out.docx"
    r = tool_registry.call(
        "xlsx.write",
        {"output": str(out), "headers": ["a"], "rows": [[1]]},
        _ctx(),
    )
    assert not r.ok and r.error.code == "unsupported_format"


# ---------------------------------------------------------------------------
# xlsx.edit_cells
# ---------------------------------------------------------------------------


def test_edit_cells_value_and_formula(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "edited.xlsx"
    r = tool_registry.call(
        "xlsx.edit_cells",
        {
            "path": str(src),
            "output": str(out),
            "sheet": "Revenue",
            "cells": [
                {"cell": "B2", "value": 99},
                {"cell": "D1", "value": "=SUM(B2:B4)"},
            ],
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["cells_written"] == 2
    assert any("xlsx.recalc" in w for w in r.warnings)

    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(str(out))
    assert wb["Revenue"]["B2"].value == 99
    assert wb["Revenue"]["D1"].value == "=SUM(B2:B4)"


def test_edit_cells_sheet_not_found(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "edited.xlsx"
    r = tool_registry.call(
        "xlsx.edit_cells",
        {
            "path": str(src),
            "output": str(out),
            "sheet": "Ghost",
            "cells": [{"cell": "A1", "value": 1}],
        },
        _ctx(),
    )
    assert not r.ok and r.error.code == "sheet_not_found"


def test_edit_cells_empty_list(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "edited.xlsx"
    r = tool_registry.call(
        "xlsx.edit_cells",
        {"path": str(src), "output": str(out), "cells": []},
        _ctx(),
    )
    assert not r.ok and r.error.code == "invalid_input"


def test_edit_cells_bad_a1(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "edited.xlsx"
    r = tool_registry.call(
        "xlsx.edit_cells",
        {"path": str(src), "output": str(out), "cells": [{"cell": "ZZ-bad", "value": 1}]},
        _ctx(),
    )
    assert not r.ok and r.error.code == "invalid_input"


# ---------------------------------------------------------------------------
# xlsx.format
# ---------------------------------------------------------------------------


def test_format_bold_and_widths(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "styled.xlsx"
    r = tool_registry.call(
        "xlsx.format",
        {
            "path": str(src),
            "output": str(out),
            "sheet": "Revenue",
            "range": "A1:B1",
            "bold": True,
            "fill_color": "FFFF00",
            "column_widths": {"A": 18, "B": 12},
        },
        _ctx(),
    )
    assert r.ok, r.error
    assert r.data["cells_formatted"] == 2

    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(str(out))
    ws = wb["Revenue"]
    assert ws["A1"].font.bold is True
    assert ws.column_dimensions["A"].width == 18


def test_format_missing_range(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "styled.xlsx"
    r = tool_registry.call(
        "xlsx.format",
        {"path": str(src), "output": str(out), "range": ""},
        _ctx(),
    )
    assert not r.ok and r.error.code == "invalid_input"


# ---------------------------------------------------------------------------
# xlsx.convert
# ---------------------------------------------------------------------------


def test_convert_xlsx_to_csv(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "rev.csv"
    r = tool_registry.call(
        "xlsx.convert",
        {"path": str(src), "output": str(out), "sheet": "Revenue"},
        _ctx(),
    )
    assert r.ok and out.is_file()
    lines = out.read_text().strip().splitlines()
    assert lines[0] == "region,net"


def test_convert_csv_to_xlsx(tmp_path):
    src = _make_csv(tmp_path)
    out = tmp_path / "loans.xlsx"
    r = tool_registry.call(
        "xlsx.convert",
        {"path": str(src), "output": str(out)},
        _ctx(),
    )
    assert r.ok and out.is_file()


def test_convert_tsv_to_csv(tmp_path):
    src = tmp_path / "x.tsv"
    src.write_text("a\tb\n1\t2\n")
    out = tmp_path / "x.csv"
    r = tool_registry.call(
        "xlsx.convert",
        {"path": str(src), "output": str(out)},
        _ctx(),
    )
    assert r.ok
    assert out.read_text() == "a,b\r\n1,2\r\n" or out.read_text() == "a,b\n1,2\n"


def test_convert_explode_sheets(tmp_path):
    src = _make_xlsx(tmp_path)
    out_dir = tmp_path / "sheets"
    r = tool_registry.call(
        "xlsx.convert",
        {"path": str(src), "output": str(out_dir), "explode_sheets": True},
        _ctx(),
    )
    assert r.ok
    assert r.data["sheet_count"] == 2
    assert (out_dir / "Revenue.csv").is_file()
    assert (out_dir / "Costs.csv").is_file()


def test_convert_extract_sheet_to_new_workbook(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "only-costs.xlsx"
    r = tool_registry.call(
        "xlsx.convert",
        {"path": str(src), "output": str(out), "sheet": "Costs"},
        _ctx(),
    )
    assert r.ok
    info = tool_registry.call("xlsx.info", {"path": str(out)}, _ctx())
    assert info.data["sheet_count"] == 1
    assert info.data["sheets"][0]["name"] == "Costs"


def test_convert_sheet_not_found(tmp_path):
    src = _make_xlsx(tmp_path)
    out = tmp_path / "x.csv"
    r = tool_registry.call(
        "xlsx.convert",
        {"path": str(src), "output": str(out), "sheet": "Ghost"},
        _ctx(),
    )
    assert not r.ok and r.error.code == "sheet_not_found"


# ---------------------------------------------------------------------------
# xlsx.recalc
# ---------------------------------------------------------------------------


def test_recalc_dependency_missing_when_no_soffice(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    src = _make_xlsx(tmp_path)
    r = tool_registry.call("xlsx.recalc", {"path": str(src)}, _ctx())
    assert not r.ok and r.error.code == "dependency_missing"


def test_recalc_file_not_found():
    r = tool_registry.call("xlsx.recalc", {"path": "/tmp/nope.xlsx"}, _ctx())
    assert not r.ok and r.error.code == "file_not_found"


def test_recalc_unsupported_format(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n")
    r = tool_registry.call("xlsx.recalc", {"path": str(p)}, _ctx())
    assert not r.ok and r.error.code == "unsupported_format"


@pytest.mark.skipif(
    shutil.which("soffice") is None and shutil.which("libreoffice") is None,
    reason="LibreOffice not installed",
)
def test_recalc_materialises_formula(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    src = tmp_path / "m.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = 10
    ws["A2"] = 20
    ws["A3"] = "=SUM(A1:A2)"
    wb.save(str(src))

    r = tool_registry.call("xlsx.recalc", {"path": str(src)}, _ctx())
    assert r.ok, r.error
    assert r.data["total_errors"] == 0

    wb2 = openpyxl.load_workbook(str(src), data_only=True)
    assert wb2.active["A3"].value == 30
