from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from ..models import Country, DocFormat

AUTHORITY = {
    Country.MX: "SAT",
    Country.BR: "SEFAZ",
    Country.CO: "DIAN",
    Country.CL: "SII",
    Country.PE: "SUNAT",
    Country.AR: "ARCA",
    Country.EC: "SRI",
}


@dataclass
class ParsedDoc:
    format: DocFormat
    country: Country
    folio: str
    uuid: str
    provider_name: str
    provider_tax_id: str
    issue_date: str
    currency: str
    subtotal: float
    tax: float
    total: float
    po_reference: Optional[str] = None
    delivery_note_ref: Optional[str] = None
    confidence: float = 1.0


def to_float(value: Optional[str], default: float = 0.0) -> float:
    if not value:
        return default
    cleaned = re.sub(r"[^0-9.,-]", "", str(value))
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return default


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _index(root: ET.Element) -> dict[str, list[ET.Element]]:
    out: dict[str, list[ET.Element]] = {}
    for el in root.iter():
        out.setdefault(_local(el.tag), []).append(el)
    return out


def _text(index: dict[str, list[ET.Element]], *names: str) -> Optional[str]:
    for name in names:
        els = index.get(name)
        if els:
            for el in els:
                if el.text and el.text.strip():
                    return el.text.strip()
    return None


def _attr(index: dict[str, list[ET.Element]], name: str, attr: str) -> Optional[str]:
    for el in index.get(name, []):
        if attr in el.attrib:
            return el.attrib[attr]
    return None


def _find_po(text: str) -> Optional[str]:
    match = re.search(r"(?:OC|PO|orden)[:\s#-]*([A-Z]{1,3}-?\d{3,})", text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _find_delivery_note(text: str) -> Optional[str]:
    match = re.search(r"(?:nota\s+de\s+entrega|remisi[oó]n|remision|gu[ií]a|DN|NE)[:\s#-]*([A-Za-z0-9-_]+)", text, re.IGNORECASE)
    if match:
        val = match.group(1).upper()
        if re.search(r"\d", val):
            return val
    ne_match = re.search(r"\b(NE-\d{3,}|DN-\d{3,}|REM-\d{3,})\b", text, re.IGNORECASE)
    return ne_match.group(1).upper() if ne_match else None


def _parse_cfdi(index, raw: str) -> ParsedDoc:
    return ParsedDoc(
        format=DocFormat.CFDI,
        country=Country.MX,
        folio=_attr(index, "Comprobante", "Folio") or _text(index, "Folio") or "s/n",
        uuid=_attr(index, "TimbreFiscalDigital", "UUID") or _text(index, "UUID") or "",
        provider_name=_attr(index, "Emisor", "Nombre") or _text(index, "Nombre") or "Proveedor",
        provider_tax_id=_attr(index, "Emisor", "Rfc") or _text(index, "Rfc") or "",
        issue_date=_attr(index, "Comprobante", "Fecha") or _text(index, "Fecha") or "",
        currency=_attr(index, "Comprobante", "Moneda") or "MXN",
        subtotal=to_float(_attr(index, "Comprobante", "SubTotal")),
        tax=to_float(_attr(index, "Impuestos", "TotalImpuestosTrasladados")),
        total=to_float(_attr(index, "Comprobante", "Total")),
        po_reference=_find_po(raw),
        delivery_note_ref=_find_delivery_note(raw),
    )


def _parse_nfe(index, raw: str) -> ParsedDoc:
    chave = _text(index, "chNFe")
    if not chave:
        id_attr = _attr(index, "infNFe", "Id")
        chave = id_attr.replace("NFe", "") if id_attr else ""
    return ParsedDoc(
        format=DocFormat.NFe,
        country=Country.BR,
        folio=_text(index, "nNF") or "s/n",
        uuid=chave or "",
        provider_name=_text(index, "xNome") or "Fornecedor",
        provider_tax_id=_text(index, "CNPJ") or "",
        issue_date=_text(index, "dhEmi") or "",
        currency="BRL",
        subtotal=to_float(_text(index, "vProd")),
        tax=to_float(_text(index, "vICMS")),
        total=to_float(_text(index, "vNF")),
        po_reference=_find_po(raw),
        delivery_note_ref=_find_delivery_note(raw),
    )


def _parse_ubl(index, raw: str) -> ParsedDoc:
    tax_id = _text(index, "ID")
    return ParsedDoc(
        format=DocFormat.SUNAT,
        country=Country.PE,
        folio=_text(index, "ID") or "s/n",
        uuid=_text(index, "UUID") or "",
        provider_name=_text(index, "RegistrationName", "Name", "PartyName") or "Proveedor",
        provider_tax_id=tax_id or "",
        issue_date=_text(index, "IssueDate") or "",
        currency=_text(index, "DocumentCurrencyCode") or "PEN",
        subtotal=to_float(_text(index, "TaxExclusiveAmount", "LineExtensionAmount")),
        tax=to_float(_text(index, "TaxAmount")),
        total=to_float(_text(index, "TaxInclusiveAmount", "PayableAmount")),
        po_reference=_find_po(raw),
        delivery_note_ref=_find_delivery_note(raw),
    )


def _parse_generic(index, raw: str) -> ParsedDoc:
    total = to_float(_text(index, "Total", "TotalAmount", "ValorTotal"))
    subtotal = to_float(_text(index, "SubTotal", "Subtotal", "Base"))
    tax = to_float(_text(index, "Impuesto", "Tax", "IVA", "TotalImpuestos"))
    uuid = _text(index, "UUID", "CUFE", "Cufe", "chNFe") or ""
    tax_id = _text(index, "NIT", "RUC", "RFC", "CNPJ", "Identificacion") or ""
    name = _text(index, "Nombre", "RazonSocial", "Emisor", "Proveedor") or "Proveedor"
    folio = _text(index, "Folio", "Numero", "Number", "Prefijo") or "s/n"
    currency = _text(index, "Moneda", "Currency", "CurrencyCode") or "COP"
    date = _text(index, "Fecha", "FechaEmision", "IssueDate") or ""
    return ParsedDoc(
        format=DocFormat.DIAN,
        country=Country.CO,
        folio=folio,
        uuid=uuid,
        provider_name=name,
        provider_tax_id=tax_id,
        issue_date=date,
        currency=currency,
        subtotal=subtotal,
        tax=tax,
        total=total,
        po_reference=_find_po(raw),
        delivery_note_ref=_find_delivery_note(raw),
        confidence=0.9,
    )


def parse(text: str, filename: str = "") -> ParsedDoc:
    """Parse a fiscal or delivery document. XML is parsed structurally; free text
    (e.g. PDF/OCR transcript or delivery note) is parsed with specialized extractors."""
    raw = text or ""
    looks_xml = raw.strip().startswith("<")

    if looks_xml:
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError(f"XML invalido: {exc}") from exc
        index = _index(root)
        root_name = _local(root.tag)
        if root_name in {"Comprobante"} or "Emisor" in index:
            return _parse_cfdi(index, raw)
        if root_name in {"nfeProc", "NFe"} or "infNFe" in index or "chNFe" in index:
            return _parse_nfe(index, raw)
        if root_name == "Invoice":
            return _parse_ubl(index, raw)
        return _parse_generic(index, raw)

    # 1. Delivery Note check (Nota de Entrega / Remisión / Albarán / NE-XXXX)
    is_delivery_note = (
        bool(re.search(r"(?:nota\s+de\s+entrega|remisi[oó]n|gu[ií]a\s+de\s+remisi[oó]n|albar[aá]n|orden\s+de\s+entrega|delivery\s+note)", raw, re.IGNORECASE))
        or bool(re.search(r"\bNE-\d{3,}\b", raw))
        or (bool(filename) and filename.lower().startswith(("ne-", "dn-", "rem-", "nota-", "albaran-")))
    )

    if is_delivery_note:
        from . import erp_data

        total_match = (
            re.search(r"(?<!sub)(?<!sub-)\b(?:TOTAL|IMPORTE\s+TOTAL|MONTO\s+TOTAL|TOTAL\s+A\s+PAGAR)\s*:\s*[$]?\s*([\d.,]+)", raw, re.IGNORECASE)
            or re.search(r"(?<!sub)(?<!sub-)\b(?:TOTAL|IMPORTE\s+TOTAL|MONTO\s+TOTAL|TOTAL\s+A\s+PAGAR)[^\d\n\r]*[$]\s*([\d.,]+)", raw, re.IGNORECASE)
            or re.search(r"(?<!sub)(?<!sub-)\b(?:TOTAL|IMPORTE\s+TOTAL|MONTO\s+TOTAL|TOTAL\s+A\s+PAGAR)\b[^\d]*([\d.,]+)", raw, re.IGNORECASE)
            or re.search(r"(?<!sub)(?<!sub-)\b(?:importe|monto|total)[^\d]*([\d.,]+)", raw, re.IGNORECASE)
        )
        if not total_match:
            raise ValueError("No se pudo extraer informacion de la nota de entrega.")

        total_val = to_float(total_match.group(1))
        sub_match = (
            re.search(r"(?:subtotal|sub-total|base)\s*:\s*[$]?\s*([\d.,]+)", raw, re.IGNORECASE)
            or re.search(r"(?:subtotal|sub-total|base)[^\d]*([\d.,]+)", raw, re.IGNORECASE)
        )
        subtotal_val = to_float(sub_match.group(1)) if sub_match else total_val
        tax_match = (
            re.search(r"(?:iva|impuesto|tax)[^\d:]*:\s*[$]?\s*([\d.,]+)", raw, re.IGNORECASE)
            or re.search(r"(?:iva|impuesto|tax)[^\d]*([\d.,]+)", raw, re.IGNORECASE)
        )
        tax_val = to_float(tax_match.group(1)) if tax_match else 0.0

        # Folio
        folio_match = (
            re.search(r"\b(NE-\d{3,}|DN-\d{3,}|REM-\d{3,})\b", raw, re.IGNORECASE)
            or re.search(r"(?:folio|n[uú]mero|nota\s+de\s+entrega)[:\s#]*([A-Za-z0-9-]+)", raw, re.IGNORECASE)
        )
        folio_val = folio_match.group(1).upper() if folio_match else "NE-5001"

        # Tax ID & Vendor
        ruc_match = re.search(r"(?:RFC|RUC|NIT|CNPJ|Tax\s*ID)[:\s]*([A-Za-z0-9.\-/]{6,})", raw, re.IGNORECASE)
        tax_id = ruc_match.group(1).strip() if ruc_match else ""

        provider_name = ""
        if tax_id and tax_id in erp_data.VENDORS:
            provider_name = erp_data.VENDORS[tax_id]
        else:
            for v_tax, v_name in erp_data.VENDORS.items():
                if v_name.lower() in raw.lower():
                    provider_name = v_name
                    if not tax_id:
                        tax_id = v_tax
                    break

        if not provider_name:
            name_match = re.search(r"(?:emisor|proveedor|remitente|de)[:\s]*([^\n\r,]+)", raw, re.IGNORECASE)
            provider_name = name_match.group(1).strip() if name_match else "Proveedor de Entrega"

        # Currency
        curr_match = re.search(r"\b(MXN|USD|COP|BRL|PEN|CLP|EUR)\b", raw, re.IGNORECASE)
        currency_val = curr_match.group(1).upper() if curr_match else "MXN"

        # Date
        date_match = re.search(r"(?:fecha|fecha\s+emisi[oó]n|fecha\s+de\s+emisi[oó]n)[:\s]*(\d{4}[-/.]\d{2}[-/.]\d{2}|\d{2}[-/.]\d{2}[-/.]\d{4})", raw, re.IGNORECASE)
        issue_date = date_match.group(1) if date_match else "2026-10-01"

        # PO & UUID
        po_ref = _find_po(raw)
        uuid_match = re.search(r"(?:UUID|CUFE|chave|chNFe)[:\s]*([A-Za-z0-9-]{8,})", raw)
        uuid_val = uuid_match.group(1) if uuid_match else f"NE-{folio_val}"

        country = Country.MX if "MXN" in currency_val or (tax_id and len(tax_id) in (12, 13)) else Country.CO

        return ParsedDoc(
            format=DocFormat.DELIVERY_NOTE,
            country=country,
            folio=folio_val,
            uuid=uuid_val,
            provider_name=provider_name,
            provider_tax_id=tax_id,
            issue_date=issue_date,
            currency=currency_val,
            subtotal=subtotal_val,
            tax=tax_val,
            total=total_val,
            po_reference=po_ref,
            delivery_note_ref=folio_val,
            confidence=0.95,
        )

    # 2. General free text (e.g. scanned PDF invoice transcript): low confidence heuristic.
    total_match = re.search(r"(?:total|importe|monto)[^\d]*([\d.,]+)", raw, re.IGNORECASE)
    uuid_match = re.search(r"(?:UUID|CUFE|chave|chNFe)[:\s]*([A-Za-z0-9-]{8,})", raw)
    ruc_match = re.search(r"(?:RUC|NIT|RFC|CNPJ)[:\s]*([A-Za-z0-9.\-/]{6,})", raw)
    if not total_match:
        raise ValueError("No se pudo extraer informacion del documento.")
    return ParsedDoc(
        format=DocFormat.PDF,
        country=Country.CO,
        folio=re.search(r"(?:folio|numero|serie)[:\s]*([A-Za-z0-9-]+)", raw, re.IGNORECASE).group(1)  # type: ignore[union-attr]
        if re.search(r"(?:folio|numero|serie)[:\s]*([A-Za-z0-9-]+)", raw, re.IGNORECASE)
        else "s/n",
        uuid=(uuid_match.group(1) if uuid_match else ""),
        provider_name="Proveedor (documento escaneado)",
        provider_tax_id=(ruc_match.group(1) if ruc_match else ""),
        issue_date="",
        currency="COP",
        subtotal=to_float(total_match.group(1)),
        tax=0.0,
        total=to_float(total_match.group(1)),
        po_reference=_find_po(raw),
        delivery_note_ref=_find_delivery_note(raw),
        confidence=0.6,
    )


def authority_for(country: Country) -> str:
    return AUTHORITY.get(country, "AUTORIDAD")
