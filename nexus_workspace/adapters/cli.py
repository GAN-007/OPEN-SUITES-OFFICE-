from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..models import EngineName, EngineStatus
from .base import AdapterNotConfigured, EngineAdapter


class CliAdapter(EngineAdapter):
    def __init__(self, engine: EngineName, command: list[str] | None, timeout: float, cwd: Path | None = None):
        self.engine = engine
        self.command = command
        self.timeout = timeout
        self.cwd = cwd

    def status(self) -> EngineStatus:
        return EngineStatus(engine=self.engine, configured=bool(self.command), transport="cli", command=self.command)

    async def execute(self, action: str, arguments: dict[str, Any]) -> Any:
        if not self.command:
            raise AdapterNotConfigured(f"{self.engine.value} CLI command is not configured")
        argv = list(self.command)
        if action and action != "run":
            argv.append(action)
        cli_args = arguments.get("argv", [])
        if not isinstance(cli_args, list) or not all(isinstance(item, str) for item in cli_args):
            raise ValueError("CLI adapter requires arguments.argv to be a list of strings")
        argv.extend(cli_args)
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(self.cwd) if self.cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"{self.engine.value} command timed out after {self.timeout}s") from None
        text = output.decode("utf-8", errors="replace")
        if process.returncode != 0:
            raise RuntimeError(f"{self.engine.value} command failed with exit code {process.returncode}:\n{text}")
        return {"exit_code": process.returncode, "output": text, "argv": argv}
