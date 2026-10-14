import pytest

from app import spreadsheet


def test_workbook_is_a_valid_xlsx():
    data = spreadsheet.build_delivery_notes_workbook()
    assert data[:2] == b"PK"
    assert len(data) > 500


def test_roundtrip_sample_rows():
    result = spreadsheet.parse_delivery_notes(spreadsheet.build_delivery_notes_workbook())
    assert result["count"] == 3
    assert result["errors"] == []
    first = result["rows"][0]
    assert first["number"] == "NE-5001"
    assert first["currency"] == "MXN"
    # delivered => received equals total
    assert first["receivedAmount"] == pytest.approx(14500.0)
    # not delivered => nothing received yet
    assert result["rows"][1]["receivedAmount"] == pytest.approx(0.0)


def test_parse_flags_bad_total_and_missing_currency():
    rows = [{"number": "NE-9000", "currency": "", "total": "no-es-numero"}]
    data = spreadsheet.build_delivery_notes_workbook(rows)
    result = spreadsheet.parse_delivery_notes(data)
    fields = {e["field"] for e in result["errors"]}
    assert "total" in fields
    assert "currency" in fields


def test_parse_accepts_string_amounts_with_thousands_sep():
    rows = [{"number": "NE-1", "currency": "MXN", "total": "14,500.50", "status": "entregada"}]
    data = spreadsheet.build_delivery_notes_workbook(rows)
    result = spreadsheet.parse_delivery_notes(data)
    assert result["errors"] == []
    assert result["rows"][0]["total"] == pytest.approx(14500.50)
    assert result["rows"][0]["receivedAmount"] == pytest.approx(14500.5)


def test_parse_rejects_non_xlsx():
    with pytest.raises(spreadsheet.SpreadsheetError):
        spreadsheet.parse_delivery_notes(b"esto no es un xlsx")


def test_parse_rejects_empty():
    with pytest.raises(spreadsheet.SpreadsheetError):
        spreadsheet.parse_delivery_notes(b"")


def test_export_empty_invoices_is_a_workbook():
    data = spreadsheet.build_invoices_workbook([])
    assert data[:2] == b"PK"
