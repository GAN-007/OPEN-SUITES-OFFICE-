from __future__ import annotations

from typing import Any

import httpx

from ..models import EngineName, EngineStatus
from .base import AdapterNotConfigured, EngineAdapter


class JsonHttpAdapter(EngineAdapter):
    def __init__(self, engine: EngineName, base_url: str | None, timeout: float):
        self.engine = engine
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout

    def status(self) -> EngineStatus:
        return EngineStatus(engine=self.engine, configured=bool(self.base_url), transport="http", endpoint=self.base_url)

    async def execute(self, action: str, arguments: dict[str, Any]) -> Any:
        if not self.base_url:
            raise AdapterNotConfigured(f"{self.engine.value} HTTP endpoint is not configured")
        path = str(arguments.pop("_path", action)).lstrip("/")
        method = str(arguments.pop("_method", "POST")).upper()
        url = f"{self.base_url}/{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method == "GET":
                response = await client.get(url, params=arguments)
            elif method == "POST":
                response = await client.post(url, json=arguments)
            elif method == "PUT":
                response = await client.put(url, json=arguments)
            elif method == "PATCH":
                response = await client.patch(url, json=arguments)
            elif method == "DELETE":
                response = await client.request("DELETE", url, json=arguments)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            response.raise_for_status()
            if not response.content:
                return {"status_code": response.status_code}
            ctype = response.headers.get("content-type", "")
            if "json" in ctype:
                return response.json()
            return {"status_code": response.status_code, "text": response.text}
