from pathlib import Path
import csv

import pytest

from runtime import tool_registry
from runtime.tool_registry import ToolCtx


def _ctx():
    return ToolCtx(
        run_id="t", user_id="u", pack_name="p",
        classification_ceiling="internal", allowed_data_sources=[],
    )


def test_read_csv(tmp_path):
    tool_registry.discover()
    p = tmp_path / "loans.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "amount"])
        w.writerow(["L1", 100])
        w.writerow(["L2", 250])
    r = tool_registry.call("xlsx.read", {"path": str(p)}, _ctx())
    assert r.ok
    assert r.data["headers"] == ["id", "amount"]
    assert r.data["row_count"] == 2


def test_read_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    tool_registry.discover()
    p = tmp_path / "loans.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["id", "amount"])
    ws.append(["L1", 100])
    wb.save(str(p))
    r = tool_registry.call("xlsx.read", {"path": str(p)}, _ctx())
    assert r.ok
    assert r.data["sheet"] == "Sheet1"
    assert r.data["row_count"] == 1


def test_read_xlsx_truncates_default_max_rows(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    tool_registry.discover()
    p = tmp_path / "big.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["id", "amount"])
    for i in range(25):
        ws.append([f"L{i}", i])
    wb.save(str(p))

    # Default max_rows is 10 — should truncate.
    r = tool_registry.call("xlsx.read", {"path": str(p)}, _ctx())
    assert r.ok
    assert r.data["row_count"] == 25            # total still reported
    assert r.data["returned_row_count"] == 10
    assert r.data["truncated"] is True
    assert len(r.data["rows"]) == 10
    assert "truncation_note" in r.data

    # max_rows=100 returns all rows; no truncation fields.
    r2 = tool_registry.call("xlsx.read", {"path": str(p), "max_rows": 100}, _ctx())
    assert r2.ok
    assert r2.data["row_count"] == 25
    assert len(r2.data["rows"]) == 25
    assert r2.data.get("truncated") is None


def test_read_csv_truncates_default_max_rows(tmp_path):
    tool_registry.discover()
    p = tmp_path / "big.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "amount"])
        for i in range(15):
            w.writerow([f"L{i}", i])
    r = tool_registry.call("xlsx.read", {"path": str(p)}, _ctx())
    assert r.ok
    assert r.data["row_count"] == 15
    assert r.data["returned_row_count"] == 10
    assert r.data["truncated"] is True


def test_read_not_found():
    tool_registry.discover()
    r = tool_registry.call("xlsx.read", {"path": "/tmp/nope.xlsx"}, _ctx())
    assert not r.ok
    assert r.error.code == "file_not_found"


def test_read_unsupported(tmp_path):
    tool_registry.discover()
    p = tmp_path / "thing.docx"
    p.write_text("x")
    r = tool_registry.call("xlsx.read", {"path": str(p)}, _ctx())
    assert not r.ok
    assert r.error.code == "unsupported_format"
