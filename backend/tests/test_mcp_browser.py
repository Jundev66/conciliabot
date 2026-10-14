from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest

from app import config, db, webmock
from app.agent import browser, erp_data, pii
from app.agent.erp import _InProcessERP, _MCPERP
from app.agent.mcp_client import MCPClient
from app.seed import DOC_CFDI_MATCH


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", os.path.join(str(tmp_path), "test.db"))
    db.init_db()
    yield


def _mcp_client() -> MCPClient:
    return MCPClient(sys.executable, ["-m", "app.mcp_server"], cwd=str(config.BASE_DIR))


def test_mcp_server_lists_readonly_tools():
    client = _mcp_client()
    try:
        names = {t["name"] for t in client.list_tools()}
        assert {"get_vendor", "get_order", "open_order_for_vendor", "get_receipts"} <= names
    finally:
        client.close()


def test_mcp_call_tool_roundtrip():
    client = _mcp_client()
    try:
        order = client.call_tool("get_order", {"number": "P-1042"})
        assert order["found"] is True
        assert order["order"]["vendor_tax_id"] == "DNO920415H19"
        assert client.call_tool("get_order", {"number": "NOPE"})["found"] is False
    finally:
        client.close()


def test_mcp_backend_matches_in_process():
    client = _mcp_client()
    try:
        mcp = _MCPERP(client)
        inproc = _InProcessERP()
        assert mcp.get_vendor("DNO920415H19") == inproc.get_vendor("DNO920415H19")
        mcp_order = mcp.open_order_for_vendor("DNO920415H19")
        inproc_order = inproc.open_order_for_vendor("DNO920415H19")
        assert mcp_order is not None and inproc_order is not None
        assert mcp_order.number == inproc_order.number
        assert mcp.get_receipts("P-1042") == inproc.get_receipts("P-1042")
    finally:
        client.close()


DEMO_TOKEN = "demo-corebiz-token"


class _Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path

        if path == "/erp-web/health":
            self._send(200, b'{"status":"ok"}', "application/json")
            return

        if path.startswith("/erp-web/order/"):
            number = path.rsplit("/", 1)[-1]
            order = erp_data.get_order(number)
            if order is None:
                self.send_response(404)
                self.end_headers()
                return
            html = webmock._page(order, erp_data.get_vendor(order.vendor_tax_id))
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return

        if self.headers.get("Authorization") != f"Bearer {DEMO_TOKEN}":
            self.send_response(401)
            self.end_headers()
            return

        if self.path.endswith("/v1/session"):
            body = json.dumps(
                {
                    "memberships": [
                        {
                            "tenantId": "t-demo",
                            "slug": "demo",
                            "name": "Comercio de Ejemplo",
                            "role": "owner",
                            "planCode": "all",
                            "isDemo": True,
                        }
                    ],
                    "tenant": {"id": "t-demo", "slug": "demo"},
                }
            ).encode("utf-8")
            self._send(200, body, "application/json")
            return

        if path == "/erp-web/v1/integrations/delivery-notes":
            items = [webmock._list_item(n) for n in erp_data.DELIVERY_NOTES.values()]
            self._send(
                200, json.dumps({"items": items, "nextCursor": None}).encode("utf-8"), "application/json"
            )
            return

        prefix = "/erp-web/v1/integrations/delivery-notes/"
        if self.path.startswith(prefix):
            note_id = urlparse(self.path).path[len(prefix) :]
            number = note_id[len("dn-") :] if note_id.startswith("dn-") else note_id
            note = erp_data.get_delivery_note(number)
            if note is None:
                self.send_response(404)
                self.end_headers()
                return
            self._send(200, json.dumps(webmock._note_view(note)).encode("utf-8"), "application/json")
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):  # noqa: D401, ANN002
        return


@pytest.fixture
def erp_web_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()


browser_only = pytest.mark.skipif(
    not (browser.is_available() and config.BROWSER_FALLBACK_ENABLED),
    reason="Playwright o el respaldo de navegador no estan disponibles",
)


@browser_only
def test_browser_fallback_reads_order(erp_web_server):
    data = browser.fetch_order(f"{erp_web_server}/erp-web/order/P-1042")
    assert data is not None
    assert data["number"] == "P-1042"
    assert data["amount"] == 14500
    assert data["vendorTaxId"] == "DNO920415H19"
    # The mock page carries an injection payload; the guard must flag it.
    assert pii.injection_suspected(data["text"])


@browser_only
def test_pipeline_includes_browser_fallback_step(erp_web_server, monkeypatch):
    from app.agent import pipeline

    monkeypatch.setattr(config, "ERP_WEB_URL", f"{erp_web_server}/erp-web/order/{{number}}")
    invoice, _ = pipeline.run_pipeline(DOC_CFDI_MATCH, "A-90001.xml", "email", use_browser=True)
    assert any(step.key == "browser" for step in invoice.pipeline)


def test_pipeline_delivery_note_demo():
    from app.agent import pipeline

    invoice, _ = pipeline.run_pipeline(
        DOC_CFDI_MATCH, "A-90002.xml", "email", delivery_note="NE-5001"
    )
    assert invoice.delivery_note is not None
    assert invoice.delivery_note.number == "NE-5001"
    assert any(step.key == "delivery_note" for step in invoice.pipeline)


def _corebiz_config(server: str, token: str = DEMO_TOKEN) -> dict:
    return {
        "provider": "corebiz",
        "corebiz": {
            "baseUrl": server,
            "apiKey": token,
            "tenantId": "t-demo",
            "tokenHeader": "Authorization",
            "tokenPrefix": "Bearer ",
            "recordsPath": "/erp-web/v1/integrations/delivery-notes",
        },
    }


def test_corebiz_connector_reads_api(erp_web_server, monkeypatch):
    from app import erp_config
    from app.agent import corebiz

    monkeypatch.setattr(erp_config, "get_config", lambda: _corebiz_config(erp_web_server))

    doc = corebiz.CorebizERP().get_document("NE-5001")
    assert doc is not None
    assert doc.amount == 14500
    assert doc.vendor_tax_id == "DNO920415H19"  # from customerTaxId
    assert doc.received_amount == 14500

    result = corebiz.CorebizERP().probe("NE-5001")
    assert result["ok"] is True
    assert result["mode"] == "api"
    assert {"health", "session", "read", "lookup"} <= {s["key"] for s in result["steps"]}


def test_corebiz_connector_rejects_bad_token(erp_web_server, monkeypatch):
    from app import erp_config
    from app.agent import corebiz

    monkeypatch.setattr(erp_config, "get_config", lambda: _corebiz_config(erp_web_server, "bad"))
    erp = corebiz.CorebizERP()
    assert corebiz.CorebizERP().get_document("NE-5001") is None
    assert erp.probe("NE-5001")["ok"] is False


def test_corebiz_probe_without_sample(erp_web_server, monkeypatch):
    from app import erp_config
    from app.agent import corebiz

    monkeypatch.setattr(erp_config, "get_config", lambda: _corebiz_config(erp_web_server))
    result = corebiz.CorebizERP().probe()
    assert result["ok"] is True
    keys = {step["key"] for step in result["steps"]}
    assert {"config", "health", "session", "read"} <= keys
