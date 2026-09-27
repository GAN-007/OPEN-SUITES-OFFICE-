from __future__ import annotations

from uuid import uuid4

from .adapters.registry import AdapterRegistry
from .database import Database
from .models import ExecuteRequest, ExecuteResult, RiskLevel, RouteRequest
from .routing import CapabilityRouter


class ApprovalRequired(PermissionError):
    pass


class NexusService:
    def __init__(self, db: Database, adapters: AdapterRegistry, router: CapabilityRouter, require_approval: bool = True):
        self.db = db
        self.adapters = adapters
        self.router = router
        self.require_approval = require_approval

    async def execute(self, request: ExecuteRequest) -> ExecuteResult:
        if self.require_approval and request.risk == RiskLevel.EXTERNAL_SIDE_EFFECT and not request.approved:
            raise ApprovalRequired("External side-effect execution requires approved=true")
        decision = self.router.route(RouteRequest(intent=request.intent, capability=request.capability, preferred_engine=request.engine))
        execution_id = str(uuid4())
        adapter = self.adapters.get(decision.engine)
        raw = await adapter.execute(request.action, dict(request.arguments))
        result_json = raw if isinstance(raw, dict) else {"result": raw}
        provenance = self.db.add_provenance(
            execution_id=execution_id,
            actor=request.actor,
            engine=decision.engine.value,
            capability=decision.capability.value,
            action=request.action,
            request_json=request.model_dump(mode="json"),
            result_json=result_json,
        )
        return ExecuteResult(
            execution_id=execution_id,
            engine=decision.engine,
            capability=decision.capability,
            action=request.action,
            result=raw,
            provenance_id=provenance.id,
        )
