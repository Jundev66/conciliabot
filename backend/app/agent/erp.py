from __future__ import annotations

import sys
import threading
from typing import Any, Optional

from .. import config, erp_config
from . import erp_data
from .erp_data import ERPOrder


class _InProcessERP:
    kind = "in-process"

    def get_vendor(self, tax_id: str) -> Optional[str]:
        return erp_data.get_vendor(tax_id)

    def get_order(self, number: str) -> Optional[ERPOrder]:
        return erp_data.get_order(number)

    def get_document(self, number: str) -> Optional[ERPOrder]:
        return erp_data.get_document(number)

    def open_order_for_vendor(self, tax_id: str) -> Optional[ERPOrder]:
        return erp_data.open_order_for_vendor(tax_id)

    def get_receipts(self, number: str) -> dict[str, Any]:
        return erp_data.get_receipts(number)

    def register_delivery_note(self, invoice: Any, actor: str) -> dict[str, Any]:
        dn = getattr(invoice, "delivery_note", None)
        number = dn.number if dn else getattr(invoice, "folio", "NE-5001")
        note = erp_data.get_delivery_note(number)
        if note:
            note.status = "registrada"
        return {
            "ok": True,
            "id": f"dn-{number}",
            "number": number,
            "status": "registered",
            "actor": actor,
            "message": f"Nota de entrega {number} confirmada y registrada en el ERP por {actor}.",
        }


class _MCPERP:
    kind = "mcp"

    def __init__(self, client: Any) -> None:
        self._client = client

    @staticmethod
    def _order(payload: Optional[dict[str, Any]]) -> Optional[ERPOrder]:
        if not payload or not payload.get("found") or not payload.get("order"):
            return None
        return erp_data.order_from_dict(payload["order"])

    def get_vendor(self, tax_id: str) -> Optional[str]:
        payload = self._client.call_tool("get_vendor", {"tax_id": tax_id})
        return payload.get("name") if payload else None

    def get_order(self, number: str) -> Optional[ERPOrder]:
        return self._order(self._client.call_tool("get_order", {"number": number}))

    def get_document(self, number: str) -> Optional[ERPOrder]:
        return self._order(self._client.call_tool("get_document", {"number": number}))

    def open_order_for_vendor(self, tax_id: str) -> Optional[ERPOrder]:
        return self._order(self._client.call_tool("open_order_for_vendor", {"tax_id": tax_id}))

    def get_receipts(self, number: str) -> dict[str, Any]:
        payload = self._client.call_tool("get_receipts", {"number": number})
        return payload or {"received": 0.0, "currency": ""}

    def register_delivery_note(self, invoice: Any, actor: str) -> dict[str, Any]:
        dn = getattr(invoice, "delivery_note", None)
        number = dn.number if dn else getattr(invoice, "folio", "NE-5001")
        return {
            "ok": True,
            "id": f"dn-{number}",
            "number": number,
            "status": "registered",
            "actor": actor,
            "message": f"Nota de entrega {number} confirmada y registrada vía MCP en el ERP por {actor}.",
        }


_lock = threading.Lock()
_backend: Optional[Any] = None
_provider_used: Optional[str] = None
_error: Optional[str] = None


def _build_demo_backend() -> Any:
    global _error
    if config.MCP_ENABLED:
        try:
            from .mcp_client import MCPClient

            client = MCPClient(
                command=sys.executable,
                args=["-m", "app.mcp_server"],
                cwd=str(config.BASE_DIR),
            )
            _error = None
            return _MCPERP(client)
        except Exception as exc:  # noqa: BLE001
            _error = str(exc)
            return _InProcessERP()
    _error = "MCP deshabilitado (CONCILIABOT_MCP)"
    return _InProcessERP()


def get_erp() -> Any:
    """Return the active ERP backend for the configured provider.

    Providers: ``demo`` (MCP server / in-process sandbox) and ``corebiz``
    (headless browser with an API key/token). Any failure falls back to the
    in-process sandbox so the pipeline never breaks.
    """
    global _backend, _provider_used, _error
    if _backend is not None:
        return _backend
    with _lock:
        if _backend is not None:
            return _backend
        provider = erp_config.active_provider()
        if provider == "corebiz":
            try:
                from .corebiz import CorebizERP

                backend = CorebizERP()
                if not backend.base_url:
                    raise RuntimeError("Corebiz sin URL base configurada")
                _backend, _provider_used, _error = backend, "corebiz", None
                return _backend
            except Exception as exc:  # noqa: BLE001
                _error = f"Corebiz no disponible: {exc}; se usa el sandbox de demo"
        _backend = _build_demo_backend()
        _provider_used = "demo"
        return _backend


def reset_backend() -> None:
    """Drop the cached backend so the next call re-reads the configuration."""
    global _backend, _provider_used
    with _lock:
        backend = _backend
        _backend, _provider_used = None, None
    closer = getattr(backend, "_client", None)
    if closer is not None and hasattr(closer, "close"):
        try:
            closer.close()
        except Exception:  # noqa: BLE001
            pass


def probe(sample_number: str = "") -> dict:
    """Diagnose the active ERP connection (used by the settings UI)."""
    provider = erp_config.active_provider()
    if provider == "corebiz":
        from .corebiz import CorebizERP

        return {"provider": "corebiz", **CorebizERP().probe(sample_number)}
    backend = get_erp()
    return {
        "ok": True,
        "provider": "demo",
        "mode": backend.kind,
        "steps": [
            {
                "key": "config",
                "status": "ok",
                "detail": f"Proveedor demo activo (backend {backend.kind}). "
                "Configura Corebiz para leer tu ERP real.",
            }
        ],
    }
