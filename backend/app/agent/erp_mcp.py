from __future__ import annotations

from typing import Any, Callable, Optional

from . import erp_data
from .erp_data import ERPOrder  # re-exported for backwards compatibility

__all__ = ["ERPOrder", "ERPMCP", "ToolNotAllowed"]

# In-process, read-only ERP sandbox. Only the tools in READ_TOOLS can be
# called, and none of them mutate state. It shares its dataset with the real
# MCP server so both transports return identical results.


class ToolNotAllowed(Exception):
    pass


class ERPMCP:
    """Read-only MCP server facade (in-process, no external transport)."""

    READ_TOOLS = {"get_vendor", "get_order", "open_order_for_vendor", "get_receipts"}

    def call_tool(self, name: str, **kwargs: Any) -> Any:
        if name not in self.READ_TOOLS:
            raise ToolNotAllowed(f"herramienta no permitida en el sandbox: {name}")
        handler: Optional[Callable[..., Any]] = getattr(self, f"_{name}", None)
        if handler is None:
            raise ToolNotAllowed(f"herramienta desconocida: {name}")
        return handler(**kwargs)

    # -- read-only tools -------------------------------------------------
    def _get_vendor(self, tax_id: str) -> Optional[str]:
        return erp_data.get_vendor(tax_id)

    def _get_order(self, number: str) -> Optional[ERPOrder]:
        return erp_data.get_order(number)

    def _open_order_for_vendor(self, tax_id: str) -> Optional[ERPOrder]:
        return erp_data.open_order_for_vendor(tax_id)

    def _get_receipts(self, number: str) -> dict[str, Any]:
        return erp_data.get_receipts(number)
