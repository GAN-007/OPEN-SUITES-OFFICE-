from __future__ import annotations

import base64
from functools import lru_cache

from fastapi import FastAPI, HTTPException

from .adapters.base import AdapterNotConfigured
from .adapters.registry import AdapterRegistry
from .assets import AssetStore
from .config import Settings
from .database import Database
from .decision_gateway import (
    DecisionPlaneNotConfigured,
    DecisionPlaneUnavailable,
    GanDecisionPlane,
)
from .models import (
    AssetCreate,
    AssetVersion,
    ExecuteRequest,
    ExecuteResult,
    RouteDecision,
    RouteRequest,
    SystemOneGatewayRequest,
)
from .routing import CapabilityRouter
from .service import ApprovalRequired, NexusService
from .system_one import SystemOneDecisionPlane


@lru_cache
def settings() -> Settings:
    return Settings()


@lru_cache
def db() -> Database:
    return Database(settings().state_db)


@lru_cache
def adapters() -> AdapterRegistry:
    return AdapterRegistry(settings())


@lru_cache
def assets() -> AssetStore:
    return AssetStore(db(), settings().artifact_dir)


@lru_cache
def decision_router() -> CapabilityRouter:
    cfg = settings()
    plane = SystemOneDecisionPlane(
        mode=cfg.system_one_mode,
        base_url=cfg.system_one_base_url,
        api_key=cfg.system_one_api_key,
        timeout_seconds=cfg.system_one_timeout_seconds,
        confidence_threshold=cfg.system_one_confidence_threshold,
    )
    return CapabilityRouter(decision_plane=plane)


@lru_cache
def service() -> NexusService:
    return NexusService(
        db(),
        adapters(),
        decision_router(),
        settings().require_approval_for_side_effects,
    )


@lru_cache
def gan_decision_plane() -> GanDecisionPlane:
    cfg = settings()
    return GanDecisionPlane(
        primary_provider=cfg.decision_plane_primary_provider,
        fallback_provider=cfg.decision_plane_fallback_provider,
        laya_base_url=cfg.laya_base_url,
        laya_api_key=cfg.laya_api_key,
        jev_base_url=cfg.jev_base_url,
        jev_api_key=cfg.jev_api_key,
        timeout_seconds=cfg.decision_plane_timeout_seconds,
    )


app = FastAPI(title="OPEN SUITES OFFICE — Nexus Control Plane", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "engines": [item.status().model_dump(mode="json") for item in adapters().adapters.values()]}


@app.get("/v1/engines")
def engines() -> list[dict]:
    return [item.status().model_dump(mode="json") for item in adapters().adapters.values()]


@app.get("/v1/systemone/health")
def system_one_health() -> dict:
    return gan_decision_plane().health()


@app.post("/v1/systemone")
def system_one_gateway(request: SystemOneGatewayRequest) -> dict:
    try:
        return gan_decision_plane().decide(request.model_dump(exclude_none=True))
    except DecisionPlaneNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DecisionPlaneUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/route", response_model=RouteDecision)
def route(request: RouteRequest) -> RouteDecision:
    return decision_router().route(request)


@app.post("/v1/execute", response_model=ExecuteResult)
async def execute(request: ExecuteRequest) -> ExecuteResult:
    try:
        return await service().execute(request)
    except ApprovalRequired as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AdapterNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/assets", response_model=AssetVersion)
def create_asset(request: AssetCreate) -> AssetVersion:
    try:
        content = base64.b64decode(request.content_base64, validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="content_base64 is not valid base64") from exc
    return assets().create(name=request.name, media_type=request.media_type, content=content, actor=request.actor)


@app.get("/v1/provenance/{provenance_id}")
def get_provenance(provenance_id: str) -> dict:
    record = db().provenance(provenance_id)
    if record is None:
        raise HTTPException(status_code=404, detail="provenance record not found")
    return {
        "id": record.id,
        "execution_id": record.execution_id,
        "actor": record.actor,
        "engine": record.engine,
        "capability": record.capability,
        "action": record.action,
        "request": record.request_json,
        "result": record.result_json,
        "created_at": record.created_at.isoformat(),
    }
