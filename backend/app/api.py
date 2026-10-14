from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from . import config, db, document_reader, erp_config, pdf_generator, security, seed, services, spreadsheet
from .agent import pipeline
from .agent import browser as browser_mod
from .agent.erp import get_erp, probe as erp_probe, reset_backend
from .evals.runner import run_evals
from .models import (
    AppSettings,
    ApprovalInput,
    AuditEntry,
    CorrectionInput,
    ErpConfig,
    IngestInput,
    Invoice,
)

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/invoices", response_model=list[Invoice])
def list_invoices() -> list[Invoice]:
    return db.list_invoices()


@router.get("/invoices/{invoice_id}", response_model=Invoice)
def get_invoice(invoice_id: str) -> Invoice:
    inv = db.get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return inv


@router.post("/invoices/{invoice_id}/approve", response_model=Invoice)
def approve_invoice(invoice_id: str, body: ApprovalInput) -> Invoice:
    try:
        return services.approve(invoice_id, body.actor)
    except KeyError:
        raise HTTPException(status_code=404, detail="Factura no encontrada")


@router.post("/invoices/{invoice_id}/confirm", response_model=Invoice)
def confirm_invoice(invoice_id: str, body: ApprovalInput) -> Invoice:
    try:
        return services.approve(invoice_id, body.actor)
    except KeyError:
        raise HTTPException(status_code=404, detail="Factura no encontrada")


@router.post("/invoices/{invoice_id}/reject", response_model=Invoice)
def reject_invoice(invoice_id: str, body: ApprovalInput) -> Invoice:
    try:
        return services.reject(invoice_id, body.actor)
    except KeyError:
        raise HTTPException(status_code=404, detail="Factura no encontrada")


@router.post("/invoices/{invoice_id}/correct", response_model=Invoice)
def correct_invoice(invoice_id: str, body: CorrectionInput) -> Invoice:
    try:
        return services.correct(invoice_id, body.actor, body.note)
    except KeyError:
        raise HTTPException(status_code=404, detail="Factura no encontrada")


_limiter = security.RateLimiter(config.RATE_LIMIT_PER_MIN, 60.0)


def _throttle(request: Request, bucket: str) -> None:
    client = request.client.host if request.client else "unknown"
    if not _limiter.allow(f"{bucket}:{client}"):
        raise HTTPException(status_code=429, detail="demasiadas solicitudes; intenta mas tarde")


@router.get("/audit", response_model=list[AuditEntry])
def get_audit() -> list[AuditEntry]:
    return db.list_audit()


@router.get("/audit/verify")
def verify_audit() -> dict:
    return db.verify_audit_chain()


@router.get("/connection")
def get_connection() -> dict:
    return erp_config.connection_meta()


@router.post("/documents/purge")
def purge_documents() -> dict:
    return {"purged": db.purge_expired_documents()}


def _xlsx_response(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_response(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/documents/template-pdf")
@router.get("/delivery-notes/sample-pdf")
def template_pdf(number: Optional[str] = None) -> Response:
    """Sample Delivery Note PDF for testing and validating with CoreBiz."""
    data = pdf_generator.build_sample_delivery_note_pdf(number=number)
    filename = f"nota-de-entrega-{number}.pdf" if number else "nota-de-entrega-ejemplo.pdf"
    return _pdf_response(data, filename)


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: str) -> Response:
    inv = db.get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    data = pdf_generator.build_invoice_voucher_pdf(inv)
    return _pdf_response(data, f"comprobante-{invoice_id}.pdf")


@router.get("/spreadsheet/template")
def spreadsheet_template() -> Response:
    """Example workbook with the CoreBiz delivery-note schema."""
    data = spreadsheet.build_delivery_notes_workbook()
    return _xlsx_response(data, "notas-de-entrega-ejemplo.xlsx")


@router.get("/spreadsheet/export")
def spreadsheet_export() -> Response:
    data = spreadsheet.build_invoices_workbook(db.list_invoices())
    return _xlsx_response(data, "conciliabot-registros.xlsx")


@router.post("/spreadsheet/import")
def spreadsheet_import(request: Request, file: UploadFile = File(...)) -> dict:
    _throttle(request, "spreadsheet")
    raw = file.file.read(spreadsheet.MAX_UPLOAD_BYTES + 1)
    if len(raw) > spreadsheet.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="archivo demasiado grande (máx. 5 MB)")
    try:
        result = spreadsheet.parse_delivery_notes(raw)
    except spreadsheet.SpreadsheetError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    result["filename"] = file.filename or ""
    return result


@router.get("/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    return db.get_settings()


@router.put("/settings", response_model=AppSettings)
def put_settings(settings: AppSettings) -> AppSettings:
    return db.save_settings(settings)


@router.post("/ingest", response_model=Invoice)
def ingest(body: IngestInput, request: Request) -> Invoice:
    _throttle(request, "ingest")
    try:
        invoice, _ = pipeline.run_pipeline(
            body.text,
            body.filename,
            body.source,
            body.use_browser,
            body.delivery_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return invoice


@router.post("/ingest/file", response_model=Invoice)
def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form("carpeta"),
    use_browser: bool = Form(False),
    delivery_note: Optional[str] = Form(None),
) -> Invoice:
    _throttle(request, "ingest")
    raw = file.file.read(spreadsheet.MAX_UPLOAD_BYTES + 1)
    if len(raw) > spreadsheet.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="archivo demasiado grande (máx. 5 MB)")

    try:
        text, detected_type, _ = document_reader.extract_text_and_meta(raw, file.filename or "documento")
    except document_reader.DocumentReaderError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        invoice, _ = pipeline.run_pipeline(
            text,
            filename=file.filename or f"documento.{detected_type}",
            source=source,
            use_browser=use_browser,
            delivery_note=delivery_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return invoice


@router.get("/tools/status")
def tools_status() -> dict:
    erp = get_erp()
    return {
        "erp": {"backend": erp.kind, "mcpEnabled": config.MCP_ENABLED},
        "browser": {
            "available": browser_mod.is_available(),
            "enabled": config.BROWSER_FALLBACK_ENABLED,
        },
    }


@router.get("/tools/mcp/tools")
def mcp_tools() -> dict:
    erp = get_erp()
    if erp.kind != "mcp":
        raise HTTPException(status_code=503, detail="servidor MCP no conectado")
    return {"tools": erp._client.list_tools()}


@router.get("/tools/browser-order/{number}")
def browser_order(number: str, request: Request) -> dict:
    _throttle(request, "browser")
    url = config.ERP_WEB_URL.format(number=number)
    try:
        data = browser_mod.fetch_order(url)
    except browser_mod.BrowserUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except security.UnsafeUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if data is None:
        raise HTTPException(status_code=404, detail="orden no encontrada en la web del ERP")
    return data


@router.get("/erp/config")
def erp_config_get() -> dict:
    return erp_config.masked_config()


@router.put("/erp/config")
def erp_config_put(body: ErpConfig) -> dict:
    patch = body.model_dump(by_alias=True)
    key = patch.get("corebiz", {}).get("apiKey") or ""
    if not key or key.startswith("***"):
        patch.get("corebiz", {}).pop("apiKey", None)
    erp_config.save_config(patch)
    reset_backend()
    return erp_config.masked_config()


@router.post("/erp/test")
def erp_test(request: Request, body: Optional[dict] = None) -> dict:
    _throttle(request, "erp-test")
    sample = (body or {}).get("sampleNumber") or ""
    try:
        return erp_probe(sample)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/reset")
def reset(request: Request) -> dict[str, str]:
    _throttle(request, "reset")
    db.reset()
    seed.seed_if_empty()
    return {"status": "reset"}


@router.post("/evals/run")
def evals_run(request: Request) -> dict:
    _throttle(request, "evals")
    return run_evals()
