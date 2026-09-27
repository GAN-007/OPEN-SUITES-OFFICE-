from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import EngineName, EngineStatus


class EngineAdapter(ABC):
    engine: EngineName

    @abstractmethod
    async def execute(self, action: str, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> EngineStatus:
        raise NotImplementedError


class AdapterNotConfigured(RuntimeError):
    pass
