from __future__ import annotations

import io
import os
import pytest
from fastapi.testclient import TestClient

from app import db, document_reader, pdf_generator, services
from app.agent import fiscal, pipeline
from app.agent.erp import reset_backend
from app.main import app
from app.models import DocFormat, InvoiceStatus


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", os.path.join(str(tmp_path), "test.db"))
    db.init_db()
    reset_backend()
    yield


def test_build_sample_delivery_note_pdf_content():
    pdf_bytes = pdf_generator.build_sample_delivery_note_pdf()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

    text, doc_type, meta = document_reader.extract_text_and_meta(pdf_bytes, "nota.pdf")
    assert doc_type == "pdf"
    assert "NE-5001" in text
    assert "DNO920415H19" in text
    assert "14,500.00" in text


def test_parse_sample_pdf_as_delivery_note():
    pdf_bytes = pdf_generator.build_sample_delivery_note_pdf()
    text, _, _ = document_reader.extract_text_and_meta(pdf_bytes, "nota.pdf")

    parsed = fiscal.parse(text, filename="nota-NE-5001.pdf")
    assert parsed.format == DocFormat.DELIVERY_NOTE
    assert parsed.folio == "NE-5001"
    assert parsed.provider_tax_id == "DNO920415H19"
    assert parsed.total == pytest.approx(14500.0)
    assert parsed.currency == "MXN"
    assert parsed.delivery_note_ref == "NE-5001"


def test_pipeline_with_pdf_delivery_note():
    pdf_bytes = pdf_generator.build_sample_delivery_note_pdf()
    text, _, _ = document_reader.extract_text_and_meta(pdf_bytes, "NE-5001.pdf")

    inv, ctx = pipeline.run_pipeline(text, filename="NE-5001.pdf", source="carpeta")
    assert inv.folio == "NE-5001"
    assert inv.delivery_note is not None
    assert inv.delivery_note.number == "NE-5001"
    assert inv.delivery_note.amount == pytest.approx(14500.0)
    assert inv.fiscal.verified is True
    assert inv.status == InvoiceStatus.matched


def test_approve_delivery_note_registers_in_corebiz():
    pdf_bytes = pdf_generator.build_sample_delivery_note_pdf()
    text, _, _ = document_reader.extract_text_and_meta(pdf_bytes, "NE-5001.pdf")

    inv, _ = pipeline.run_pipeline(text, filename="NE-5001.pdf", source="api")
    assert inv.status == InvoiceStatus.matched

    # Human confirms / approves delivery note
    approved_inv = services.approve(inv.id, actor="Almacén Central")
    assert approved_inv.status == InvoiceStatus.registered
    assert approved_inv.approved_by == "Almacén Central"

    # Verify audit chain recorded the registration
    audits = [a for a in db.list_audit() if a.invoice_id == inv.id]
    actions = [a.action for a in audits]
    assert "approved" in actions
    assert "registered" in actions


def test_api_endpoints_pdf_and_file_ingest():
    from app import security

    token = security.load_or_create_token()
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)

    # 1. Download template PDF
    res = client.get("/api/documents/template-pdf", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    pdf_bytes = res.content
    assert pdf_bytes.startswith(b"%PDF")

    # 2. Upload file via /api/ingest/file
    files = {"file": ("nota-ejemplo.pdf", pdf_bytes, "application/pdf")}
    res_ingest = client.post("/api/ingest/file", files=files, data={"source": "api"}, headers=headers)
    assert res_ingest.status_code == 200
    data = res_ingest.json()
    inv_id = data["id"]
    assert data["folio"] == "NE-5001"
    assert data["status"] == "matched"
    assert data["deliveryNote"]["number"] == "NE-5001"

    # 3. Confirm and register in CoreBiz
    res_confirm = client.post(f"/api/invoices/{inv_id}/confirm", json={"actor": "Supervisor CoreBiz"}, headers=headers)
    assert res_confirm.status_code == 200
    confirmed = res_confirm.json()
    assert confirmed["status"] == "registered"
    assert confirmed["approvedBy"] == "Supervisor CoreBiz"

    # 4. Download invoice voucher PDF
    res_pdf = client.get(f"/api/invoices/{inv_id}/pdf", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"


def test_approve_registration_failure_does_not_mark_registered(monkeypatch):
    from app.agent import erp

    class FailingERP:
        kind = "corebiz"

        def register_delivery_note(self, inv, actor):
            return {"ok": False, "message": "CoreBiz respondió HTTP 404: {'errorKind':'NotFound'}"}

    monkeypatch.setattr(erp, "get_erp", lambda: FailingERP())

    pdf_bytes = pdf_generator.build_sample_delivery_note_pdf()
    text, _, _ = document_reader.extract_text_and_meta(pdf_bytes, "NE-5001.pdf")
    inv, _ = pipeline.run_pipeline(text, filename="NE-5001.pdf", source="api")

    approved_inv = services.approve(inv.id, actor="María López")
    assert approved_inv.status == InvoiceStatus.approved
    assert approved_inv.status != InvoiceStatus.registered
    assert "falló el registro" in approved_inv.note
    assert "404" in approved_inv.note
