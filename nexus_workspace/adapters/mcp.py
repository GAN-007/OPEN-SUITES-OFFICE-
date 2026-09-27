from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import httpx

from ..models import EngineName, EngineStatus
from .base import AdapterNotConfigured, EngineAdapter


class McpHttpAdapter(EngineAdapter):
    def __init__(self, engine: EngineName, endpoint: str | None, timeout: float):
        self.engine = engine
        self.endpoint = endpoint
        self.timeout = timeout
        self.session_id: str | None = None

    def status(self) -> EngineStatus:
        return EngineStatus(engine=self.engine, configured=bool(self.endpoint), transport="mcp-http", endpoint=self.endpoint)

    async def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        if not self.endpoint:
            raise AdapterNotConfigured(f"{self.engine.value} MCP endpoint is not configured")
        payload = {"jsonrpc": "2.0", "id": str(uuid4()), "method": method, "params": params}
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload, headers=headers)
            response.raise_for_status()
            new_session = response.headers.get("Mcp-Session-Id")
            if new_session:
                self.session_id = new_session
            ctype = response.headers.get("content-type", "")
            if "text/event-stream" in ctype:
                for line in response.text.splitlines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                        if data.get("id") == payload["id"]:
                            if "error" in data:
                                raise RuntimeError(data["error"])
                            return data.get("result")
                raise RuntimeError("MCP SSE response did not contain a matching JSON-RPC result")
            data = response.json()
            if "error" in data:
                raise RuntimeError(data["error"])
            return data.get("result")

    async def execute(self, action: str, arguments: dict[str, Any]) -> Any:
        if action == "tools/list":
            return await self._rpc("tools/list", {})
        return await self._rpc("tools/call", {"name": action, "arguments": arguments})
