from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..models import EngineName, EngineStatus
from .base import AdapterNotConfigured, EngineAdapter


class PageIndexAdapter(EngineAdapter):
    engine = EngineName.PAGEINDEX

    def __init__(self, upstream_path: Path):
        self.upstream_path = upstream_path

    def status(self) -> EngineStatus:
        configured = (self.upstream_path / "pageindex").exists()
        return EngineStatus(engine=self.engine, configured=configured, transport="python-sdk", endpoint=str(self.upstream_path))

    async def execute(self, action: str, arguments: dict[str, Any]) -> Any:
        if not (self.upstream_path / "pageindex").exists():
            raise AdapterNotConfigured("PageIndex submodule is not initialized. Run git submodule update --init --recursive.")
        if action not in {"submit_document", "chat"}:
            raise ValueError("PageIndex adapter supports submit_document and chat")
        code = (
            "import json,sys; "
            f"sys.path.insert(0,{str(self.upstream_path)!r}); "
            "from pageindex import PageIndexClient; "
            "a=json.loads(sys.stdin.read()); c=PageIndexClient(); "
            + ("r=c.submit_document(a['path'], wait=a.get('wait', True)); " if action == "submit_document" else "r=c.chat(a['query'], doc_id=a['doc_id']); ")
            + "print(json.dumps(r if isinstance(r,(dict,list,str,int,float,bool,type(None))) else {'result':str(r)}, default=str))"
        )
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(__import__("json").dumps(arguments).encode())
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode(errors="replace"))
        return __import__("json").loads(stdout.decode())
