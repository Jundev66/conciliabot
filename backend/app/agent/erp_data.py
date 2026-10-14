from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

# Shared, read-only ERP dataset. It backs both the in-process sandbox
# (erp_mcp.ERPMCP) and the standalone MCP server (app.mcp_server), so the same
# source of truth is served over either transport.


@dataclass
class ERPOrder:
    number: str
    vendor_tax_id: str
    amount: float
    currency: str
    received_amount: float


@dataclass
class DeliveryNote:
    number: str
    vendor_tax_id: str
    amount: float
    currency: str
    received_amount: float
    status: str = "abierta"


VENDORS: dict[str, str] = {
    "DNO920415H19": "Distribuidora del Norte S.A. de C.V.",
    "APM010203K55": "Aceros y Perfiles Monterrey S.A.",
    "14200166000187": "Metalurgica Paulista Ltda.",
    "9001234567": "Servicios Logisticos Andinos S.A.S.",
    "PCB050607L22": "Papeleria Corporativa del Bajio S.A.",
    "20123456789": "Insumos Industriales del Pacifico S.A.C.",
    "J-30456789-1": "Bodega La Esquina",
    "J-30456789-2": "Ferreteria El Tornillo",
    "J-30456789-3": "Supermercado Los Andes",
    "J-30456789-4": "Panaderia Santa Rosa",
    "J-30456789-5": "Restaurante Dona Carmen",
}

ORDERS: dict[str, ERPOrder] = {
    "P-1042": ERPOrder("P-1042", "DNO920415H19", 14500, "MXN", 14500),
    "P-1043": ERPOrder("P-1043", "APM010203K55", 15950, "MXN", 15950),
    "P-1044": ERPOrder("P-1044", "14200166000187", 9912, "BRL", 9912),
    "P-1045": ERPOrder("P-1045", "9001234567", 4998000, "COP", 4800000),
    "P-1046": ERPOrder("P-1046", "20123456789", 8024, "PEN", 8024),
    "P-1041": ERPOrder("P-1041", "PCB050607L22", 3712, "MXN", 3712),
}

# Notas de entrega / remisiones. En Corebiz este es el flujo principal: la
# factura del proveedor debe cuadrar contra la nota de entrega por numero,
# importe y recepcion.
DELIVERY_NOTES: dict[str, DeliveryNote] = {
    "NE-5001": DeliveryNote("NE-5001", "DNO920415H19", 14500, "MXN", 14500),
    "NE-5002": DeliveryNote("NE-5002", "APM010203K55", 15950, "MXN", 15950),
    "NE-5003": DeliveryNote("NE-5003", "14200166000187", 9912, "BRL", 9912),
    "NE-5004": DeliveryNote("NE-5004", "9001234567", 4998000, "COP", 4800000, "parcial"),
    "NE-5005": DeliveryNote("NE-5005", "20123456789", 8024, "PEN", 8024),
    "NE-5006": DeliveryNote("NE-5006", "PCB050607L22", 3712, "MXN", 3712),
    "NE-000001": DeliveryNote("NE-000001", "J-30456789-1", 91.35, "USD", 0.0),
    "NE-000002": DeliveryNote("NE-000002", "J-30456789-2", 65.42, "USD", 0.0),
    "NE-000003": DeliveryNote("NE-000003", "J-30456789-3", 169.07, "USD", 0.0),
    "NE-000004": DeliveryNote("NE-000004", "J-30456789-4", 119.71, "USD", 0.0),
    "NE-000005": DeliveryNote("NE-000005", "J-30456789-5", 44.14, "USD", 44.14, "entregada"),
}


def get_delivery_note(number: str) -> Optional[DeliveryNote]:
    return DELIVERY_NOTES.get(number)


def open_delivery_notes_for_vendor(tax_id: str) -> list[DeliveryNote]:
    return [n for n in DELIVERY_NOTES.values() if n.vendor_tax_id == tax_id]


def get_document(number: str) -> Optional[ERPOrder]:
    """Look up any ERP document (orden de compra o nota de entrega) by number."""
    order = ORDERS.get(number)
    if order:
        return order
    note = DELIVERY_NOTES.get(number)
    if note:
        return ERPOrder(
            number=note.number,
            vendor_tax_id=note.vendor_tax_id,
            amount=note.amount,
            currency=note.currency,
            received_amount=note.received_amount,
        )
    return None


def get_vendor(tax_id: str) -> Optional[str]:
    return VENDORS.get(tax_id)


def get_order(number: str) -> Optional[ERPOrder]:
    return ORDERS.get(number)


def open_order_for_vendor(tax_id: str) -> Optional[ERPOrder]:
    for order in ORDERS.values():
        if order.vendor_tax_id == tax_id:
            return order
    return None


def get_receipts(number: str) -> dict[str, Any]:
    order = ORDERS.get(number)
    if not order:
        return {"received": 0.0, "currency": ""}
    return {"received": order.received_amount, "currency": order.currency}


def order_to_dict(order: ERPOrder) -> dict[str, Any]:
    return asdict(order)


def order_from_dict(data: dict[str, Any]) -> ERPOrder:
    return ERPOrder(
        number=data["number"],
        vendor_tax_id=data["vendor_tax_id"],
        amount=float(data["amount"]),
        currency=data["currency"],
        received_amount=float(data["received_amount"]),
    )
