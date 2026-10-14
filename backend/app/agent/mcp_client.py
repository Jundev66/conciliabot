from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# A thin, synchronous MCP client. The MCP SDK is asyncio-native, so we host the
# session inside a dedicated event-loop thread and expose blocking helpers to
# the (synchronous) pipeline. The stdio context managers are entered and exited
# in the same thread/loop, as the transport requires.


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(
        self,
        command: str,
        args: list[str],
        cwd: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        start_timeout: float = 20.0,
    ) -> None:
        self._command = command
        self._args = args
        self._cwd = cwd
        self._env = env
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._session: Optional[ClientSession] = None
        self._error: Optional[BaseException] = None
        self._stop: Optional[asyncio.Event] = None
        self._call_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name="mcp-client", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=start_timeout):
            raise MCPError("tiempo de espera agotado al iniciar el servidor MCP")
        if self._error is not None:
            raise MCPError(f"no se pudo iniciar el servidor MCP: {self._error!r}")

    # -- lifecycle ------------------------------------------------------
    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except BaseException as exc:  # noqa: BLE001 - surface to the caller
            self._error = exc
            self._ready.set()

    async def _main(self) -> None:
        self._stop = asyncio.Event()
        params = StdioServerParameters(
            command=self._command,
            args=self._args,
            cwd=self._cwd,
            env=self._env,
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    self._ready.set()
                    await self._stop.wait()
        except BaseException as exc:  # noqa: BLE001
            self._error = exc
            self._ready.set()

    def close(self) -> None:
        if self._stop is None:
            return
        try:
            self._loop.call_soon_threadsafe(self._stop.set)
            self._thread.join(timeout=10)
        except Exception:  # noqa: BLE001
            pass

    # -- blocking helpers ----------------------------------------------
    def _run_coro(self, coro, timeout: float = 30.0) -> Any:
        if self._session is None:
            raise MCPError(f"sesion MCP no disponible: {self._error!r}")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            raise MCPError(f"fallo la llamada MCP: {exc}") from exc

    def list_tools(self) -> list[dict[str, Any]]:
        with self._call_lock:
            result = self._run_coro(self._session.list_tools())  # type: ignore[union-attr]
        tools = []
        for tool in result.tools:
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                }
            )
        return tools

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        with self._call_lock:
            result = self._run_coro(
                self._session.call_tool(name, arguments or {})  # type: ignore[union-attr]
            )
        return _parse_result(result)


def _parse_result(result: Any) -> Any:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return None
