from __future__ import annotations

import io
import json
from typing import Any, Optional

from pypdf import PdfReader


class DocumentReaderError(Exception):
    pass


def extract_text_from_pdf(raw_bytes: bytes) -> str:
    """Extract clean text from PDF bytes using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages_text: list[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t.strip())
        extracted = "\n\n".join(pages_text).strip()
        if not extracted:
            raise DocumentReaderError("El archivo PDF no contiene texto legible (posible imagen escaneada sin OCR).")
        return extracted
    except Exception as exc:
        if isinstance(exc, DocumentReaderError):
            raise
        raise DocumentReaderError(f"Error al leer archivo PDF: {exc}") from exc


def extract_text_from_json(raw_bytes: bytes) -> str:
    """Format structured delivery note / invoice JSON into text for the fiscal parser."""
    try:
        data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise DocumentReaderError(f"JSON inválido: {exc}") from exc

    # If it's a list or dict with items (e.g. CoreBiz Page<item>)
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list) and data["items"]:
            data = data["items"][0]

    if not isinstance(data, dict):
        return json.dumps(data, indent=2, ensure_ascii=False)

    lines: list[str] = []
    # Identify fields
    number = data.get("number") or data.get("folio") or data.get("id") or "s/n"
    lines.append(f"NOTA DE ENTREGA / FOLIO: {number}")
    if data.get("customerName") or data.get("vendorName") or data.get("providerName"):
        name = data.get("customerName") or data.get("vendorName") or data.get("providerName")
        lines.append(f"Emisor/Cliente: {name}")
    if data.get("customerTaxId") or data.get("vendorTaxId") or data.get("taxId"):
        tax_id = data.get("customerTaxId") or data.get("vendorTaxId") or data.get("taxId")
        lines.append(f"RFC/Tax ID: {tax_id}")
    if data.get("issuedAt") or data.get("issueDate") or data.get("fecha"):
        lines.append(f"Fecha: {data.get('issuedAt') or data.get('issueDate') or data.get('fecha')}")
    if data.get("currency") or data.get("moneda"):
        lines.append(f"Moneda: {data.get('currency') or data.get('moneda')}")
    if data.get("subtotal"):
        lines.append(f"Subtotal: {data.get('subtotal')}")
    if data.get("tax") or data.get("iva"):
        lines.append(f"IVA: {data.get('tax') or data.get('iva')}")
    if data.get("total"):
        lines.append(f"Total: {data.get('total')}")
    if data.get("receivedAmount"):
        lines.append(f"Recibido: {data.get('receivedAmount')}")
    if data.get("status"):
        lines.append(f"Estado: {data.get('status')}")
    if data.get("receivedBy"):
        lines.append(f"Recibido por: {data.get('receivedBy')}")

    # Add items if present
    items = data.get("lines") or data.get("items")
    if isinstance(items, list):
        lines.append("Items:")
        for idx, it in enumerate(items, 1):
            if isinstance(it, dict):
                desc = it.get("description") or it.get("name") or f"Item {idx}"
                qty = it.get("quantity") or 1
                price = it.get("unitPrice") or 0
                tot = it.get("lineTotal") or 0
                lines.append(f"  {idx}. {desc} - Cant: {qty} - P.Unit: {price} - Total: {tot}")

    return "\n".join(lines)


def extract_text_from_xlsx(raw_bytes: bytes) -> str:
    """Read first row or summary of Excel sheet for ingest."""
    try:
        from .spreadsheet import parse_delivery_notes

        parsed = parse_delivery_notes(raw_bytes)
        rows = parsed.get("rows") or []
        if not rows:
            raise DocumentReaderError("El archivo Excel no contiene notas de entrega legibles.")
        first = rows[0]
        lines = [
            f"NOTA DE ENTREGA: {first.get('number', 'NE-5001')}",
            f"Emisor/Cliente: {first.get('customerName', '')}",
            f"Moneda: {first.get('currency', 'MXN')}",
            f"Total: {first.get('total', 0)}",
            f"Recibido: {first.get('receivedAmount', 0)}",
            f"Estado: {first.get('status', 'entregada')}",
            f"Fecha emisión: {first.get('issuedAt', '')}",
            f"Fecha entrega: {first.get('deliveredAt', '')}",
            f"Recibido por: {first.get('receivedBy', '')}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        if isinstance(exc, DocumentReaderError):
            raise
        raise DocumentReaderError(f"Error al leer archivo Excel: {exc}") from exc


def extract_text_and_meta(raw_bytes: bytes, filename: str) -> tuple[str, str, dict[str, Any]]:
    """Determine document format and extract text representation.
    Returns (extracted_text, detected_type, meta_dict).
    """
    fn = (filename or "").lower()
    is_pdf = fn.endswith(".pdf") or raw_bytes.startswith(b"%PDF-")
    is_xlsx = fn.endswith((".xlsx", ".xlsm")) or raw_bytes.startswith(b"PK\x03\x04")
    is_json = fn.endswith(".json") or (raw_bytes.strip().startswith(b"{") and raw_bytes.strip().endswith(b"}"))
    is_xml = fn.endswith(".xml") or raw_bytes.strip().startswith(b"<")

    if is_pdf:
        text = extract_text_from_pdf(raw_bytes)
        return text, "pdf", {"filename": filename, "format": "PDF"}

    if is_json:
        text = extract_text_from_json(raw_bytes)
        return text, "json", {"filename": filename, "format": "JSON"}

    if is_xlsx and not is_xml:
        text = extract_text_from_xlsx(raw_bytes)
        return text, "xlsx", {"filename": filename, "format": "XLSX"}

    # Default to text / XML decoded
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1", errors="replace")

    detected = "xml" if is_xml else "text"
    return text, detected, {"filename": filename, "format": detected.upper()}
