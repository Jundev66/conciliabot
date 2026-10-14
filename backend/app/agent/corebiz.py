from __future__ import annotations

from typing import Any, Optional

import httpx

from .. import erp_config, security
from . import browser
from .erp_data import ERPOrder

# CoreBiz exposes a REST API (NestJS) at the base URL, with no global prefix.
# For machines there is a dedicated, read-only integration namespace guarded by
# a machine API key (no user session):
#
#   GET /health                                       public, no token
#   GET /v1/integrations/delivery-notes?status&limit&cursor  Bearer API key -> Page<item>
#   GET /v1/integrations/delivery-notes/{id}          Bearer API key -> view
#
# Auth is `Authorization: Bearer <api key>`. The tenant is fixed server-side by
# the integration config (INTEGRATIONS_TENANT_ID), so `x-corebiz-tenant` is not
# required; it is still sent when configured. There is no lookup-by-number
# endpoint and no `search` filter, so a document is found by paging the list and
# matching its `number`, then reading the full view by id. If the base URL
# answers with HTML instead of JSON, a headless-browser read is attempted and
# reported as unmet (mode "html") so selectors can be added.
#
# NOTE: CoreBiz notes are DOCUMENTS OF SALE (its own customer), not supplier
# invoices. The counterparty field available in the view is `customerName`; the
# tax id is only present if the installation exposes `customerTaxId`.

_DEFAULT_RECORDS_PATH = "/v1/integrations/delivery-notes"
_PAGE_LIMIT = 100
_MAX_PAGES = 20


def _to_float(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("$", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


class CorebizERP:
    kind = "corebiz"

    def __init__(self) -> None:
        cfg = erp_config.get_config().get("corebiz", {})
        self.base_url = (cfg.get("baseUrl") or "").rstrip("/")
        self.api_key = cfg.get("apiKey") or ""
        self.tenant_id = cfg.get("tenantId") or ""
        self.token_header = cfg.get("tokenHeader") or "Authorization"
        prefix = cfg.get("tokenPrefix")
        self.token_prefix = "Bearer " if prefix is None else prefix
        self.records_path = (cfg.get("recordsPath") or _DEFAULT_RECORDS_PATH).rstrip("/") or (
            _DEFAULT_RECORDS_PATH
        )

    # -- helpers --------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"accept": "application/json"}
        if self.api_key:
            headers[self.token_header] = f"{self.token_prefix}{self.api_key}"
        if self.tenant_id:
            headers["x-corebiz-tenant"] = self.tenant_id
        return headers

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}{path}"

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> httpx.Response:
        url = security.validate_outbound_url(self._url(path), purpose="corebiz")
        return httpx.get(url, headers=self._headers(), params=params, timeout=20.0)

    # -- probes ---------------------------------------------------------
    def health(self) -> httpx.Response:
        return self._get("/health")

    def session(self) -> httpx.Response:
        return self._get("/v1/session")

    # -- reads ----------------------------------------------------------
    def list_notes(
        self, *, status: Optional[str] = None, limit: int = _PAGE_LIMIT, cursor: Optional[str] = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        res = self._get(self.records_path, params=params)
        res.raise_for_status()
        payload = res.json()
        if not isinstance(payload, dict):
            return {"items": [], "nextCursor": None}
        return payload

    def find_note(self, number: str) -> Optional[dict[str, Any]]:
        cursor: Optional[str] = None
        for _ in range(_MAX_PAGES):
            page = self.list_notes(cursor=cursor)
            items = page.get("items") or []
            for item in items:
                if isinstance(item, dict) and str(item.get("number")) == number:
                    return item
            cursor = page.get("nextCursor")
            if not cursor:
                break
        return None

    def get_order(self, number: str) -> Optional[ERPOrder]:
        return self.get_document(number)

    def get_document(self, number: str) -> Optional[ERPOrder]:
        try:
            item = self.find_note(number)
        except (httpx.HTTPError, ValueError):
            return None
        if item is None:
            return None
        view = item
        note_id = item.get("id")
        if note_id:
            res = self._get(f"{self.records_path}/{note_id}")
            if res.status_code == 200:
                try:
                    data = res.json()
                    if isinstance(data, dict):
                        view = data
                except ValueError:
                    view = item
        return self._as_document(number, view)

    @staticmethod
    def _as_document(number: str, view: dict[str, Any]) -> ERPOrder:
        total = _to_float(view.get("total"))
        if "receivedAmount" in view:
            received = _to_float(view.get("receivedAmount"))
        else:
            status = str(view.get("status") or "").lower()
            delivered = view.get("deliveredAt") not in (None, "")
            received = (
                total
                if delivered or status in {"delivered", "entregada", "recibida", "received"}
                else 0.0
            )
        return ERPOrder(
            number=str(view.get("number") or number),
            vendor_tax_id=str(view.get("customerTaxId") or ""),
            amount=total,
            currency=str(view.get("currency") or ""),
            received_amount=received,
        )

    # -- ERP interface (used by the pipeline) ---------------------------
    def get_vendor(self, tax_id: str) -> Optional[str]:
        return None

    def open_order_for_vendor(self, tax_id: str) -> Optional[ERPOrder]:
        return None

    def get_receipts(self, number: str) -> dict[str, Any]:
        doc = self.get_document(number)
        if doc is None:
            return {"received": 0.0, "currency": ""}
        return {"received": doc.received_amount, "currency": doc.currency}

    def register_delivery_note(self, invoice: Any, actor: str) -> dict[str, Any]:
        """Confirm and register a delivery note or invoice receipt into CoreBiz."""
        from datetime import datetime, timezone
        dn = getattr(invoice, "delivery_note", None)
        number = dn.number if dn else getattr(invoice, "folio", "NE-5001")
        total = getattr(invoice, "total", 0.0)
        currency = getattr(invoice, "currency", "MXN")
        prov_name = getattr(invoice.provider, "name", "") if hasattr(invoice, "provider") else ""
        prov_tax_id = getattr(invoice.provider, "tax_id", "") if hasattr(invoice, "provider") else ""

        payload = {
            "number": number,
            "status": "delivered",
            "confirmedBy": actor,
            "receivedBy": actor,
            "confirmedAt": datetime.now(timezone.utc).isoformat(),
            "invoiceId": getattr(invoice, "id", ""),
            "invoiceFolio": getattr(invoice, "folio", ""),
            "total": f"{total:.2f}",
            "currency": currency,
            "customerName": prov_name,
            "customerTaxId": prov_tax_id,
        }

        note_id = None
        try:
            item = self.find_note(number)
            if item:
                note_id = item.get("id")
        except Exception:
            note_id = None

        target_url = (
            f"{self.records_path}/{note_id}/confirm"
            if note_id
            else self.records_path
        )

        try:
            url = security.validate_outbound_url(self._url(target_url), purpose="corebiz")
            res = httpx.post(url, json=payload, headers=self._headers(), timeout=20.0)
            if res.status_code in (200, 201):
                data = _safe_json(res) or {}
                msg = data.get("message") or f"Nota de entrega {number} registrada exitosamente en CoreBiz."
                if dn and hasattr(dn, "amount"):
                    dn.received_amount = dn.amount
                return {
                    "ok": True,
                    "id": data.get("id") or note_id or f"dn-{number}",
                    "number": number,
                    "status": "registered",
                    "actor": actor,
                    "message": msg,
                }
            elif res.status_code == 404 and note_id:
                url2 = security.validate_outbound_url(self._url(self.records_path), purpose="corebiz")
                res2 = httpx.post(url2, json=payload, headers=self._headers(), timeout=20.0)
                if res2.status_code in (200, 201):
                    data = _safe_json(res2) or {}
                    msg = data.get("message") or f"Nota de entrega {number} registrada exitosamente en CoreBiz."
                    if dn and hasattr(dn, "amount"):
                        dn.received_amount = dn.amount
                    return {
                        "ok": True,
                        "id": data.get("id") or f"dn-{number}",
                        "number": number,
                        "status": "registered",
                        "actor": actor,
                        "message": msg,
                    }
            return {
                "ok": False,
                "number": number,
                "status": "failed",
                "message": f"CoreBiz respondió HTTP {res.status_code}: {res.text[:120]}",
            }
        except Exception as exc:
            return {
                "ok": False,
                "number": number,
                "status": "error",
                "message": f"No se pudo conectar a CoreBiz para registrar: {exc}",
            }

    # -- diagnostics ----------------------------------------------------
    def probe(self, sample_number: str = "") -> dict[str, Any]:
        steps: list[dict[str, str]] = []

        def step(key: str, status: str, detail: str) -> None:
            steps.append({"key": key, "status": status, "detail": detail})

        if not self.base_url:
            step("config", "error", "Falta la URL base de CoreBiz (COREBIZ_BASE_URL).")
            return {"ok": False, "steps": steps}
        step(
            "config",
            "ok",
            f"base={self.base_url}; header={self.token_header}; "
            f"empresa={self.tenant_id or '(la del token)'}; "
            + (
                f"token presente ({len(self.api_key)} chars)."
                if self.api_key
                else "token AUSENTE."
            ),
        )

        try:
            res = self.health()
        except (httpx.HTTPError, security.UnsafeUrlError) as exc:
            step("health", "error", f"No se pudo contactar {self.base_url}: {exc}")
            return {"ok": False, "steps": steps}
        step(
            "health",
            "ok" if res.status_code < 500 else "warning",
            f"GET /health -> HTTP {res.status_code}.",
        )

        try:
            res = self.session()
        except (httpx.HTTPError, security.UnsafeUrlError) as exc:
            step("session", "warning", f"GET /v1/session no respondio: {exc}")
        else:
            if res.status_code == 200:
                data = _safe_json(res)
                memberships = data.get("memberships") if isinstance(data, dict) else None
                tenant = data.get("tenant") if isinstance(data, dict) else None
                tenant_id = (tenant or {}).get("id") if isinstance(tenant, dict) else None
                detail = f"GET /v1/session -> HTTP 200; {len(memberships or [])} empresa(s)"
                if tenant_id:
                    detail += f"; activa={tenant_id}"
                elif self.tenant_id:
                    detail += f"; enviando x-corebiz-tenant={self.tenant_id}"
                step("session", "ok", detail)
            elif res.status_code == 401:
                # A machine API key is not a user session: 401 here is expected and the
                # read below is what actually proves the credential.
                step(
                    "session",
                    "warning",
                    "GET /v1/session -> HTTP 401 (normal: la clave de integracion de "
                    "maquina no es una sesion de usuario; se valida con la lectura).",
                )
            else:
                step("session", "warning", f"GET /v1/session -> HTTP {res.status_code}.")

        try:
            page = self.list_notes(limit=1)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            status = "error" if code in (401, 403) else "warning"
            step("read", status, f"GET {self.records_path}?limit=1 -> HTTP {code}.")
            return {"ok": False, "steps": steps}
        except (httpx.HTTPError, ValueError) as exc:
            detail = f"GET {self.records_path} no devolvio JSON: {exc}"
            if browser.is_available():
                detail += " (hay navegador headless; harian falta selectores para tu interfaz)."
            step("read", "warning", detail)
            return {"ok": True, "steps": steps, "mode": "html"}
        items = page.get("items") or []
        step("read", "ok", f"GET {self.records_path}?limit=1 -> {len(items)} nota(s).")

        if sample_number:
            try:
                doc = self.get_document(sample_number)
            except (httpx.HTTPError, security.UnsafeUrlError) as exc:
                step("lookup", "warning", f"No se pudo leer {sample_number}: {exc}")
                return {"ok": True, "steps": steps, "mode": "api"}
            if doc is not None:
                step("lookup", "ok", f"Nota {sample_number}: {doc.currency} {doc.amount:,.2f}.")
                return {"ok": True, "steps": steps, "mode": "api", "sample": doc.__dict__}
            step("lookup", "warning", f"No se encontro la nota {sample_number} en el listado.")
            return {"ok": True, "steps": steps, "mode": "api"}

        return {"ok": True, "steps": steps, "mode": "api"}


def _safe_json(res: httpx.Response) -> Any:
    try:
        return res.json()
    except ValueError:
        return None
