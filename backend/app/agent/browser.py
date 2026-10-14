from __future__ import annotations

from typing import Any, Optional

from .. import config, security

# Browser fallback / connector for ERPs that expose only a web UI. It runs a
# headless, locked-down browser: it only navigates and reads. It never fills or
# submits forms, never downloads files, and blocks navigation to non-web URLs.
# Whatever it reads is treated as UNTRUSTED input (the pipeline still runs the
# prompt-injection guard over its text).


class BrowserUnavailable(RuntimeError):
    pass


class BrowserReadOnlyError(RuntimeError):
    pass


def _launch_args() -> list[str]:
    """Chromium flags. The OS sandbox stays ON unless explicitly disabled."""
    args = ["--disable-dev-shm-usage", "--disable-gpu"]
    if config.BROWSER_NO_SANDBOX:
        args.append("--no-sandbox")
    return args


def is_available() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return True


class BrowserSession:
    """A locked-down, read-only headless browser with optional auth headers."""

    def __init__(self, headers: dict[str, str] | None = None, timeout_ms: int = 15000) -> None:
        self._headers = headers or {}
        self._timeout_ms = timeout_ms
        self._pw = None
        self._browser = None
        self._context = None

    def __enter__(self) -> "BrowserSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserUnavailable("Playwright no esta instalado") from exc
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True, args=_launch_args())
        except Exception as exc:  # noqa: BLE001
            raise BrowserUnavailable(f"no se pudo iniciar Chromium: {exc}") from exc
        self._context = self._browser.new_context(
            java_script_enabled=True,
            accept_downloads=False,
            ignore_https_errors=config.BROWSER_INSECURE,
            extra_http_headers=self._headers,
        )
        self._context.route("**/*", _route)
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            if self._pw is not None:
                self._pw.stop()

    def fetch(self, url: str) -> dict:
        """Navigate and return status + JSON (if any) + visible text."""
        url = security.validate_outbound_url(url, purpose="browser")
        page = self._context.new_page()  # type: ignore[union-attr]
        page.set_default_timeout(self._timeout_ms)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
            status = response.status if response is not None else 0
            payload = None
            if response is not None:
                try:
                    payload = response.json()
                except Exception:  # noqa: BLE001 - not JSON, ignore
                    payload = None
            text = ""
            if page.query_selector("body"):
                text = page.inner_text("body")
            return {"status": status, "json": payload, "text": text, "url": page.url}
        finally:
            page.close()


def _route(route) -> None:
    url = route.request.url
    if url.startswith(("http://", "https://", "data:")):
        route.continue_()
    else:
        route.abort()


_READ_EXPR = """
() => {
  const el = document.querySelector('[data-erp-order]');
  if (!el) return null;
  const d = el.dataset;
  return {
    number: d.orderNumber || null,
    vendorTaxId: d.vendorTaxId || null,
    amount: d.amount ? Number(d.amount) : null,
    currency: d.currency || null,
    receivedAmount: d.receivedAmount ? Number(d.receivedAmount) : null,
    vendorName: d.vendorName || null,
    text: (el.innerText || '').slice(0, 2000),
  };
}
"""


def fetch_order(url: str, timeout_ms: int = 15000) -> dict | None:
    """Read an order from an ERP web page. Returns ``None`` if not present."""
    url = security.validate_outbound_url(url, purpose="browser")
    with BrowserSession(timeout_ms=timeout_ms) as session:
        page = session._context.new_page()  # type: ignore[union-attr]
        page.set_default_timeout(timeout_ms)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            data = page.evaluate(_READ_EXPR)
            if not data:
                return None
            data["source_url"] = url
            return data
        finally:
            page.close()
