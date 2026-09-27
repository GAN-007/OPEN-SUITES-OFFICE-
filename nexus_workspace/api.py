from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .adapters.base import AdapterNotConfigured
from .adapters.registry import AdapterRegistry
from .assets import AssetStore
from .config import Settings
from .database import Database
from .models import (
    AssetCreate,
    AssetVersion,
    EngineName,
    ExecuteRequest,
    ExecuteResult,
    RouteDecision,
    RouteRequest,
)
from .routing import CapabilityRouter
from .runtime import NativeProcessManager, RuntimeCatalog
from .service import ApprovalRequired, NexusService


@lru_cache
def settings() -> Settings:
    return Settings()


@lru_cache
def db() -> Database:
    return Database(settings().state_db)


@lru_cache
def runtime_catalog() -> RuntimeCatalog:
    return RuntimeCatalog(settings().runtime_manifest, Path.cwd())


@lru_cache
def process_manager() -> NativeProcessManager:
    return NativeProcessManager(runtime_catalog(), settings().runtime_state_dir)


@lru_cache
def adapters() -> AdapterRegistry:
    return AdapterRegistry(settings(), Path.cwd())


@lru_cache
def assets() -> AssetStore:
    return AssetStore(db(), settings().artifact_dir)


@lru_cache
def service() -> NexusService:
    return NexusService(
        db(),
        adapters(),
        CapabilityRouter(),
        settings().require_approval_for_side_effects,
    )


app = FastAPI(title="OPEN SUITES OFFICE — Nexus Control Plane", version="0.2.0")


@app.get("/")
def root() -> dict:
    return {
        "name": "OPEN SUITES OFFICE — Nexus",
        "version": "0.2.0",
        "storage_model": "vendored-source-tree",
        "engine_count": len(list(EngineName)),
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "storage_model": "vendored-source-tree",
        "engines": [
            {
                **item.status().model_dump(mode="json"),
                "native": process_manager().process_status(item.engine),
            }
            for item in adapters().adapters.values()
        ],
    }


@app.get("/v1/engines")
def engines() -> list[dict]:
    return [
        {
            **adapter.status().model_dump(mode="json"),
            "native": process_manager().process_status(adapter.engine),
        }
        for adapter in adapters().adapters.values()
    ]


@app.get("/v1/native/engines")
def native_engines() -> list[dict]:
    return [process_manager().process_status(spec.engine) for spec in runtime_catalog().all()]


@app.get("/v1/native/engines/{engine}")
def native_engine(engine: EngineName) -> dict:
    return process_manager().process_status(engine)


@app.post("/v1/native/engines/{engine}/start")
def native_engine_start(engine: EngineName) -> dict:
    try:
        return process_manager().start(engine)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/native/engines/{engine}/stop")
def native_engine_stop(engine: EngineName) -> dict:
    try:
        return process_manager().stop(engine)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/native/engines/{engine}/{phase}")
def native_engine_phase(engine: EngineName, phase: str) -> dict:
    if phase not in {"install", "build", "test"}:
        raise HTTPException(status_code=404, detail="phase must be install, build, or test")
    try:
        results = process_manager().run_phase(engine, phase)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"engine": engine.value, "phase": phase, "results": results}


@app.post("/v1/route", response_model=RouteDecision)
def route(request: RouteRequest) -> RouteDecision:
    return CapabilityRouter().route(request)


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
    return assets().create(
        name=request.name,
        media_type=request.media_type,
        content=content,
        actor=request.actor,
    )


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
