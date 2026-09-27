from __future__ import annotations

import json
from pathlib import Path

import typer
import uvicorn

from .adapters.registry import AdapterRegistry
from .config import Settings
from .models import Capability, EngineName, RouteRequest
from .routing import CapabilityRouter
from .source_resolver import EngineSourceResolver

app = typer.Typer(no_args_is_help=True, help="Nexus control-plane CLI")


@app.command()
def serve() -> None:
    cfg = Settings()
    uvicorn.run(
        "nexus_workspace.api:app",
        host=cfg.host,
        port=cfg.port,
        reload=False,
    )


@app.command()
def route(
    intent: str,
    capability: Capability | None = None,
    engine: EngineName | None = None,
) -> None:
    decision = CapabilityRouter().route(
        RouteRequest(
            intent=intent,
            capability=capability,
            preferred_engine=engine,
        )
    )
    typer.echo(json.dumps(decision.model_dump(mode="json"), indent=2))


@app.command("source-status")
def source_status() -> None:
    cfg = Settings()
    resolver = EngineSourceResolver(
        Path.cwd(),
        cfg.engine_source_mode,
        cfg.engine_dir,
        cfg.upstream_dir,
    )
    typer.echo(
        json.dumps([resolver.status(engine) for engine in EngineName], indent=2)
    )


@app.command("engine-status")
def engine_status() -> None:
    registry = AdapterRegistry(Settings(), Path.cwd())
    typer.echo(
        json.dumps(
            [
                adapter.status().model_dump(mode="json")
                for adapter in registry.adapters.values()
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    app()
