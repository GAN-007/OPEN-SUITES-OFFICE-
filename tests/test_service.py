from __future__ import annotations

from typing import Any

import pytest

from nexus_workspace.adapters.base import EngineAdapter
from nexus_workspace.models import EngineName, EngineStatus, ExecuteRequest, RiskLevel
from nexus_workspace.routing import CapabilityRouter
from nexus_workspace.service import ApprovalRequired, NexusService


class FakeAdapter(EngineAdapter):
    def __init__(self, engine: EngineName):
        self.engine = engine

    async def execute(self, action: str, arguments: dict[str, Any]) -> Any:
        return {"action": action, "arguments": arguments, "ok": True}

    def status(self) -> EngineStatus:
        return EngineStatus(engine=self.engine, configured=True, transport="fake")


class FakeRegistry:
    def __init__(self):
        self.adapters = {engine: FakeAdapter(engine) for engine in EngineName}

    def get(self, engine: EngineName) -> EngineAdapter:
        return self.adapters[engine]


@pytest.mark.asyncio
async def test_execution_records_provenance(temp_db) -> None:
    service = NexusService(temp_db, FakeRegistry(), CapabilityRouter(), require_approval=True)
    result = await service.execute(ExecuteRequest(intent="remember this decision", action="remember", arguments={"text": "x"}))
    assert result.engine == EngineName.COGNEE
    record = temp_db.provenance(result.provenance_id)
    assert record is not None
    assert record.engine == EngineName.COGNEE.value


@pytest.mark.asyncio
async def test_external_side_effect_requires_explicit_approval(temp_db) -> None:
    service = NexusService(temp_db, FakeRegistry(), CapabilityRouter(), require_approval=True)
    with pytest.raises(ApprovalRequired):
        await service.execute(ExecuteRequest(intent="submit browser form", action="submit", risk=RiskLevel.EXTERNAL_SIDE_EFFECT))
