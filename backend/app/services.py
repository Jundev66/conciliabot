from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from . import db
from .models import AuditEntry, Invoice, InvoiceStatus


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log(
    invoice_id: str,
    action: str,
    actor: str,
    detail: str,
    at: Optional[str] = None,
    connection_id: Optional[str] = None,
) -> AuditEntry:
    entry = AuditEntry(
        id="",
        invoice_id=invoice_id,
        action=action,
        actor=actor,
        detail=detail,
        at=at or now_iso(),
    )
    return db.append_audit(entry, connection_id=connection_id)


def approve(invoice_id: str, actor: str, connection_id: Optional[str] = None) -> Invoice:
    cid = connection_id or db.default_connection_id()
    inv = db.get_invoice(invoice_id, connection_id=cid)
    if not inv:
        raise KeyError(invoice_id)
    settings = db.get_settings()
    at = now_iso()

    from .agent.erp import get_erp
    erp = get_erp()
    reg_res: dict = {}
    try:
        reg_res = erp.register_delivery_note(inv, actor)
    except Exception as exc:  # noqa: BLE001
        reg_res = {"ok": False, "message": str(exc)}

    erp_label = "CoreBiz" if getattr(erp, "kind", "") == "corebiz" else settings.erp
    inv.approved_by = actor
    inv.approved_at = at

    if reg_res.get("ok"):
        inv.status = InvoiceStatus.registered
        msg = reg_res.get("message", f"Registrada con éxito en {erp_label}.")
        inv.note = msg
        if inv.delivery_note and hasattr(inv.delivery_note, "amount"):
            inv.delivery_note.received_amount = inv.delivery_note.amount
        db.store_invoice(inv, connection_id=cid)
        log(invoice_id, "approved", "usuario", f"Aprobada y confirmada por {actor}.", at, connection_id=cid)
        log(
            invoice_id,
            "registered",
            "corebiz",
            f"Registrada con éxito en {erp_label} por {actor}. Ref: {reg_res.get('id', 'OK')}. {msg}",
            at,
            connection_id=cid,
        )
        db.record_approval(invoice_id, actor, "approved", msg, connection_id=cid)
    else:
        inv.status = InvoiceStatus.approved
        err_msg = reg_res.get("message", f"Error al registrar en {erp_label}")
        inv.note = f"Aprobada por {actor}, pero falló el registro en {erp_label}: {err_msg}"
        db.store_invoice(inv, connection_id=cid)
        log(invoice_id, "approved", "usuario", f"Aprobada por {actor}. Pendiente registro en {erp_label}.", at, connection_id=cid)
        log(
            invoice_id,
            "registration_failed",
            "sistema",
            f"Fallo en {erp_label}: {err_msg}",
            at,
            connection_id=cid,
        )
        db.record_approval(invoice_id, actor, "approved_pending_registration", err_msg, connection_id=cid)

    return inv


def reject(invoice_id: str, actor: str, connection_id: Optional[str] = None) -> Invoice:
    cid = connection_id or db.default_connection_id()
    inv = db.get_invoice(invoice_id, connection_id=cid)
    if not inv:
        raise KeyError(invoice_id)
    inv.status = InvoiceStatus.rejected
    db.store_invoice(inv, connection_id=cid)
    log(invoice_id, "rejected", "usuario", f"Rechazada por {actor}. No se registra nada.", connection_id=cid)
    db.record_approval(invoice_id, actor, "rejected", "", connection_id=cid)
    return inv


def correct(
    invoice_id: str, actor: str, note: str, connection_id: Optional[str] = None
) -> Invoice:
    cid = connection_id or db.default_connection_id()
    inv = db.get_invoice(invoice_id, connection_id=cid)
    if not inv:
        raise KeyError(invoice_id)
    at = now_iso()
    inv.approved_by = actor
    inv.approved_at = at

    from .agent.erp import get_erp
    erp = get_erp()
    reg_res: dict = {}
    try:
        reg_res = erp.register_delivery_note(inv, actor)
    except Exception as exc:  # noqa: BLE001
        reg_res = {"ok": False, "message": str(exc)}

    erp_label = "CoreBiz" if getattr(erp, "kind", "") == "corebiz" else "ERP"

    if reg_res.get("ok"):
        inv.status = InvoiceStatus.registered
        msg = reg_res.get("message", "")
        inv.note = f"{note} | {msg}" if msg else note
        if inv.delivery_note and hasattr(inv.delivery_note, "amount"):
            inv.delivery_note.received_amount = inv.delivery_note.amount
        db.store_invoice(inv, connection_id=cid)
        log(invoice_id, "corrected", "usuario", f"Correccion de {actor}: {note}", at, connection_id=cid)
        log(invoice_id, "approved", "usuario", f"Aprobada con correccion por {actor}.", at, connection_id=cid)
        log(
            invoice_id,
            "registered",
            "corebiz",
            f"Registrada en {erp_label} tras corrección humana. {msg}",
            at,
            connection_id=cid,
        )
        db.record_approval(invoice_id, actor, "corrected", note, connection_id=cid)
    else:
        inv.status = InvoiceStatus.approved
        err_msg = reg_res.get("message", f"Error al registrar en {erp_label}")
        inv.note = f"{note} | Falló registro en {erp_label}: {err_msg}"
        db.store_invoice(inv, connection_id=cid)
        log(invoice_id, "corrected", "usuario", f"Correccion de {actor}: {note}", at, connection_id=cid)
        log(invoice_id, "approved", "usuario", f"Aprobada con correccion por {actor}, pero falló el registro en {erp_label}.", at, connection_id=cid)
        log(
            invoice_id,
            "registration_failed",
            "sistema",
            f"Fallo en {erp_label}: {err_msg}",
            at,
            connection_id=cid,
        )
        db.record_approval(invoice_id, actor, "corrected_pending_registration", f"{note} | {err_msg}", connection_id=cid)

    return inv

