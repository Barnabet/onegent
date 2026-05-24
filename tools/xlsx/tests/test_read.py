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
