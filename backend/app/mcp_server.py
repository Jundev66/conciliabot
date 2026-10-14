from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .agent import erp_data

# Real MCP server exposing the (read-only) ERP tools. It can be consumed by the
# agent through ``app.agent.mcp_client`` or by any MCP host (Claude Desktop,
# MCP Inspector, etc.) via stdio:
#
#     python -m app.mcp_server

server = MCPServer(
    "conciliabot-erp",
    instructions=(
        "ERP de solo lectura para conciliacion de facturas. Todas las herramientas "
        "son de consulta; no existe ninguna operacion de escritura."
    ),
)


@server.tool(description="Devuelve el nombre del proveedor a partir de su identificador fiscal.")
def get_vendor(tax_id: str) -> dict[str, Any]:
    name = erp_data.get_vendor(tax_id)
    return {"found": name is not None, "tax_id": tax_id, "name": name}


@server.tool(description="Devuelve una orden de compra por su numero.")
def get_order(number: str) -> dict[str, Any]:
    order = erp_data.get_order(number)
    return {
        "found": order is not None,
        "order": erp_data.order_to_dict(order) if order else None,
    }


@server.tool(description="Devuelve la orden de compra abierta para un proveedor.")
def open_order_for_vendor(tax_id: str) -> dict[str, Any]:
    order = erp_data.open_order_for_vendor(tax_id)
    return {
        "found": order is not None,
        "order": erp_data.order_to_dict(order) if order else None,
    }


@server.tool(description="Devuelve cualquier documento del ERP (orden de compra o nota de entrega) por numero.")
def get_document(number: str) -> dict[str, Any]:
    document = erp_data.get_document(number)
    return {
        "found": document is not None,
        "order": erp_data.order_to_dict(document) if document else None,
    }


@server.tool(description="Devuelve las recepciones registradas para una orden de compra.")
def get_receipts(number: str) -> dict[str, Any]:
    return erp_data.get_receipts(number)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
