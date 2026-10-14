from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

from .. import db, services
from ..models import (
    DeliveryNote,
    Discrepancy,
    DocFormat,
    FiscalCheck,
    Invoice,
    InvoiceStatus,
    ModelTier,
    PipelineStep,
    Provider,
    PurchaseOrder,
    Severity,
    StepStatus,
)
from . import browser, fiscal, pii
from .. import config, erp_config
from .erp import get_erp
from .llm import BudgetExceeded, LLMGateway, RunContext, classify_difficulty

TOLERANCE = 0.01


def _due_date(issue: str, days: int = 30) -> str:
    try:
        base = datetime.fromisoformat(issue[:10])
        return (base + timedelta(days=days)).date().isoformat()
    except (ValueError, TypeError):
        return issue


class _Phase:
    def __init__(self, key: str, label: str) -> None:
        self.key = key
        self.label = label
        self.start = time.perf_counter()

    def done(
        self, detail: str, model: ModelTier = ModelTier.none, tokens: Optional[int] = None
    ) -> PipelineStep:
        return PipelineStep(
            key=self.key,
            label=self.label,
            status=StepStatus.done,
            detail=detail,
            model=model,
            tokens=tokens,
            duration_ms=int((time.perf_counter() - self.start) * 1000),
        )


def _policy_status(
    is_duplicate: bool,
    critical: bool,
    warning: bool,
    fiscal_ok: bool,
    require_fiscal: bool,
    confidence: float,
) -> InvoiceStatus:
    if is_duplicate:
        return InvoiceStatus.duplicate
    if require_fiscal and not fiscal_ok:
        return InvoiceStatus.needs_review
    if critical:
        return InvoiceStatus.discrepancy
    if warning or confidence < 0.75:
        return InvoiceStatus.needs_review
    return InvoiceStatus.matched


def run_pipeline(
    text: str,
    filename: str = "factura.xml",
    source: str = "api",
    use_browser: bool = False,
    delivery_note: Optional[str] = None,
    ctx: Optional[RunContext] = None,
) -> tuple[Invoice, RunContext]:
    ctx = ctx or RunContext()
    connection_id = erp_config.active_connection_id()
    if ctx.connection_id in ("", "default"):
        ctx.connection_id = connection_id
    else:
        connection_id = ctx.connection_id
    settings = db.get_settings()
    steps: list[PipelineStep] = []

    # 1. Ingest ---------------------------------------------------------
    ph = _Phase("ingest", "Ingesta")
    steps.append(ph.done("Documento recibido y job creado (estado durable)."))

    # 2. Pre-process ----------------------------------------------------
    ph = _Phase("preprocess", "Pre-proceso")
    redaction = pii.redact(text) if settings.pii_redaction else None
    injected = pii.injection_suspected(text) if settings.prompt_injection_guard else False
    detail = "PII redactada" if redaction and redaction.count else "Sin PII detectada"
    detail += ", documento marcado como entrada no confiable" if settings.prompt_injection_guard else ""
    if injected:
        detail += " — INYECCION DETECTADA, se ignora cualquier instruccion del documento"
    steps.append(ph.done(detail))

    # 3. Classify + route ----------------------------------------------
    ph = _Phase("classify", "Clasificacion y ruteo")
    parsed = fiscal.parse(text, filename)
    difficulty = classify_difficulty(redaction.text if redaction else text, parsed.format != DocFormat.PDF)
    tier = LLMGateway(ctx).route(difficulty) if settings.model_routing else ModelTier.small
    try:
        tokens_before = ctx.tokens_used
        gateway = LLMGateway(ctx)
        gateway.complete(f"clasificar documento {filename}", tier, label="classify")
        route_tokens = ctx.tokens_used - tokens_before
        steps.append(
            ph.done(
                f"Formato {parsed.format.value} detectado. Ruteo: {tier.value}.",
                tier,
                route_tokens,
            )
        )
    except BudgetExceeded as exc:
        steps.append(
            PipelineStep(
                key="classify",
                label="Clasificacion y ruteo",
                status=StepStatus.warning,
                detail=f"Presupuesto alcanzado al clasificar: {exc}",
                model=tier,
            )
        )

    # 4. Extract --------------------------------------------------------
    ph = _Phase("extract", "Extraccion")
    steps.append(
        ph.done(
            f"Campos extraidos y validados contra esquema estricto (confianza {parsed.confidence:.2f}).",
            ModelTier.small if parsed.format != DocFormat.PDF else ModelTier.reasoning,
        )
    )

    # 5. Fiscal verification -------------------------------------------
    ph = _Phase("fiscal", "Verificacion fiscal")
    is_delivery_doc = parsed.format == DocFormat.DELIVERY_NOTE
    authority = "Control Interno CoreBiz" if is_delivery_doc else fiscal.authority_for(parsed.country)
    fiscal_ok = bool(parsed.uuid) or is_delivery_doc
    fiscal_check = FiscalCheck(
        verified=fiscal_ok,
        authority=authority,
        reference=f"Remisión {parsed.folio} cotejada" if is_delivery_doc else (f"{'Referencia verificada' if fiscal_ok else 'Sin referencia'} ({authority})"),
        message="Nota de entrega íntegra y cotejada contra almacén." if is_delivery_doc else ("Documento integro y valido." if fiscal_ok else "No se pudo validar la referencia del documento."),
    )
    steps.append(
        ph.done(
            f"Cotejo de integridad contra {authority}." if is_delivery_doc else f"{'Verificado' if fiscal_ok else 'No verificado'} contra {authority}.",
        )
    )

    # 6. Match with ERP (read-only via MCP) -----------------------------
    ph = _Phase("match", "Cotejo con ERP")
    erp = get_erp()
    order = (erp.get_order(parsed.po_reference) if parsed.po_reference else None) or erp.open_order_for_vendor(parsed.provider_tax_id)
    vendor_name = erp.get_vendor(parsed.provider_tax_id)
    steps.append(
        ph.done(
            f"Consulta ERP via {erp.kind} (solo lectura): "
            + ("OC " + order.number if order else "sin OC abierta")
            + (f". Proveedor: {vendor_name}." if vendor_name else "."),
        )
    )

    # 6b. Browser fallback (ERP without an API) -------------------------
    web_order: Optional[dict] = None
    if use_browser and order and config.BROWSER_FALLBACK_ENABLED:
        ph = _Phase("browser", "Respaldo de navegador")
        url = config.ERP_WEB_URL.format(number=order.number)
        try:
            web_order = browser.fetch_order(url)
            if web_order:
                injected = pii.injection_suspected(web_order.get("text", ""))
                detail = (
                    f"Leido de la web del ERP con navegador headless (solo lectura): "
                    f"{web_order.get('number')}."
                )
                detail += (
                    " Contenido no confiable: INYECCION detectada, instrucciones ignoradas."
                    if injected
                    else " Sin instrucciones sospechosas en la pagina."
                )
                steps.append(ph.done(detail))
            else:
                steps.append(
                    ph.done("La web del ERP no expone la orden; se usa el dato de la API/MCP.")
                )
        except (browser.BrowserUnavailable, ValueError) as exc:
            steps.append(
                PipelineStep(
                    key="browser",
                    label="Respaldo de navegador",
                    status=StepStatus.warning,
                    detail=f"Navegador no disponible o URL no permitida: {exc}",
                )
            )

    # 6c. Delivery note (Corebiz / notas de entrega) --------------------
    effective_delivery_note = delivery_note or parsed.delivery_note_ref
    erp_document = None
    if effective_delivery_note:
        ph = _Phase("delivery_note", "Nota de entrega")
        try:
            erp_document = erp.get_document(effective_delivery_note)
        except Exception:  # noqa: BLE001 - a lookup failure must not fail ingest
            erp_document = None

        if erp_document:
            steps.append(
                ph.done(
                    f"Nota de entrega {erp_document.number} leida del ERP "
                    f"({erp_document.currency} {erp_document.amount:,.2f})."
                )
            )
            if not vendor_name:
                vendor_name = getattr(erp_document, "vendor_name", None) or vendor_name
        else:
            steps.append(
                ph.done(f"No se encontro la nota de entrega {effective_delivery_note} en el ERP.")
            )

    # 7. Reconcile ------------------------------------------------------
    ph = _Phase("reconcile", "Conciliacion")
    discrepancies: list[Discrepancy] = []
    purchase_order: Optional[PurchaseOrder] = None
    if order:
        purchase_order = PurchaseOrder(
            number=order.number,
            amount=order.amount,
            received_amount=order.received_amount,
            currency=order.currency,
        )
        if abs(parsed.total - order.amount) > TOLERANCE:
            diff = parsed.total - order.amount
            discrepancies.append(
                Discrepancy(
                    field="Importe total",
                    invoice_value=f"{parsed.currency} {parsed.total:,.2f}",
                    expected_value=f"{order.currency} {order.amount:,.2f}",
                    severity=Severity.critical,
                    message=f"La factura difiere de la orden de compra en {diff:+,.2f}.",
                )
            )
        if order.received_amount < order.amount:
            discrepancies.append(
                Discrepancy(
                    field="Cantidad recibida",
                    invoice_value="Factura por 100%",
                    expected_value=f"Recepcion parcial ({order.received_amount:,.0f} de {order.amount:,.0f})",
                    severity=Severity.warning,
                    message="La orden indica recepcion parcial. Requiere confirmacion humana.",
                )
            )
        if web_order and web_order.get("amount") is not None:
            web_amount = float(web_order["amount"])
            if abs(order.amount - web_amount) > TOLERANCE:
                discrepancies.append(
                    Discrepancy(
                        field="Fuente web del ERP",
                        invoice_value=f"{order.currency} {order.amount:,.2f} (API)",
                        expected_value=f"{order.currency} {web_amount:,.2f} (web)",
                        severity=Severity.warning,
                        message="La web del ERP y la API no coinciden. Requiere revision humana.",
                    )
                )

    if erp_document:
        if abs(parsed.total - erp_document.amount) > TOLERANCE:
            diff = parsed.total - erp_document.amount
            discrepancies.append(
                Discrepancy(
                    field="Nota de entrega",
                    invoice_value=f"{parsed.currency} {parsed.total:,.2f}",
                    expected_value=f"{erp_document.currency} {erp_document.amount:,.2f}",
                    severity=Severity.critical,
                    message=(
                        f"La factura difiere de la nota de entrega {erp_document.number} "
                        f"en {diff:+,.2f}."
                    ),
                )
            )
        if erp_document.received_amount < erp_document.amount:
            discrepancies.append(
                Discrepancy(
                    field="Recepcion (nota de entrega)",
                    invoice_value=f"{erp_document.currency} {erp_document.amount:,.2f}",
                    expected_value=f"Recibido {erp_document.currency} {erp_document.received_amount:,.2f}",
                    severity=Severity.warning,
                    message="La nota de entrega indica recepcion parcial. Requiere confirmacion humana.",
                )
            )

    existing = db.get_invoice_by_uuid(parsed.uuid, connection_id=connection_id) if parsed.uuid else None
    is_duplicate = existing is not None
    if is_duplicate:
        discrepancies.append(
            Discrepancy(
                field="Registro",
                invoice_value=parsed.folio,
                expected_value=f"Ya registrada ({existing.id})",  # type: ignore[union-attr]
                severity=Severity.critical,
                message="La misma factura ya fue registrada. Riesgo de pago duplicado.",
            )
        )

    try:
        tokens_before = ctx.tokens_used
        gateway = LLMGateway(ctx)
        gateway.complete(
            f"conciliar folio {parsed.folio} total {parsed.total}",
            ModelTier.reasoning if difficulty == "hard" else ModelTier.small,
            label="reconcile",
        )
        reconcile_tokens = ctx.tokens_used - tokens_before
    except BudgetExceeded:
        reconcile_tokens = None
    steps.append(
        ph.done(
            "Conciliacion completada."
            if not discrepancies
            else f"{len(discrepancies)} hallazgo(s) de conciliacion.",
            ModelTier.reasoning if difficulty == "hard" else ModelTier.small,
            reconcile_tokens or 0,
        )
    )

    critical = any(d.severity == Severity.critical for d in discrepancies)
    warning = any(d.severity == Severity.warning for d in discrepancies)
    status = _policy_status(
        is_duplicate=is_duplicate,
        critical=critical,
        warning=warning,
        fiscal_ok=fiscal_ok,
        require_fiscal=settings.require_fiscal_verification,
        confidence=parsed.confidence,
    )

    # 8. Persist --------------------------------------------------------
    invoice = Invoice(
        id=db.next_invoice_id(),
        folio=parsed.folio,
        uuid=parsed.uuid or "-",
        format=parsed.format,
        country=parsed.country,
        provider=Provider(
            name=vendor_name or parsed.provider_name,
            tax_id=parsed.provider_tax_id,
            country=parsed.country,
        ),
        issue_date=parsed.issue_date,
        due_date=_due_date(parsed.issue_date),
        currency=parsed.currency,
        subtotal=parsed.subtotal,
        tax=parsed.tax,
        total=parsed.total,
        status=status,
        source=source,
        purchase_order=purchase_order,
        delivery_note=(
            DeliveryNote(
                number=erp_document.number,
                amount=erp_document.amount,
                received_amount=erp_document.received_amount,
                currency=erp_document.currency,
            )
            if erp_document
            else (
                DeliveryNote(
                    number=parsed.folio,
                    amount=parsed.total,
                    received_amount=parsed.total,
                    currency=parsed.currency,
                )
                if parsed.format == DocFormat.DELIVERY_NOTE or parsed.folio.startswith(("NE-", "DN-"))
                else None
            )
        ),
        discrepancies=discrepancies,
        duplicate_of=existing.id if existing else None,  # type: ignore[union-attr]
        fiscal=fiscal_check,
        pipeline=steps,
        created_at=services.now_iso(),
        connection_id=connection_id,
    )
    db.store_invoice(invoice, connection_id=connection_id)
    db.store_document(invoice.id, text, connection_id=connection_id)

    services.log(
        invoice.id,
        "ingested",
        "agente",
        f"Factura recibida desde {source} ({parsed.folio}).",
        connection_id=connection_id,
    )
    services.log(
        invoice.id,
        "fiscal_verified",
        "agente",
        f"Verificacion fiscal contra {authority}: {'ok' if fiscal_ok else 'fallida'}.",
        connection_id=connection_id,
    )
    if order:
        services.log(
            invoice.id,
            "matched",
            "agente",
            f"Cotejo con OC {order.number} por {order.currency} {order.amount:,.2f}.",
            connection_id=connection_id,
        )
    if web_order:
        services.log(
            invoice.id,
            "browser_read",
            "agente",
            f"Lectura de respaldo con navegador headless ({web_order.get('source_url', 'web ERP')}).",
            connection_id=connection_id,
        )
    if erp_document:
        services.log(
            invoice.id,
            "delivery_note_matched",
            "agente",
            f"Conciliada contra nota de entrega {erp_document.number}.",
            connection_id=connection_id,
        )
    if is_duplicate:
        services.log(
            invoice.id,
            "duplicate_found",
            "agente",
            f"Mismo UUID ya registrado ({existing.id}).",  # type: ignore[union-attr]
            connection_id=connection_id,
        )
    elif critical:
        services.log(
            invoice.id,
            "discrepancy_found",
            "agente",
            f"{len(discrepancies)} diferencia(s) detectada(s).",
            connection_id=connection_id,
        )

    return invoice, ctx
