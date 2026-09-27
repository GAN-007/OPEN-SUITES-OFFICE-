from __future__ import annotations

import json
from pathlib import Path

import typer
import uvicorn

from .adapters.registry import AdapterRegistry
from .config import Settings
from .models import Capability, EngineName, RouteRequest
from .routing import CapabilityRouter
from .runtime import NativeProcessManager, RuntimeCatalog

app = typer.Typer(no_args_is_help=True, help="Nexus unified AI workspace CLI")
engine_app = typer.Typer(no_args_is_help=True, help="Manage vendored native engines")
app.add_typer(engine_app, name="engine")


def _settings() -> Settings:
    return Settings()


def _catalog() -> RuntimeCatalog:
    cfg = _settings()
    return RuntimeCatalog(cfg.runtime_manifest, Path.cwd())


def _manager() -> NativeProcessManager:
    cfg = _settings()
    return NativeProcessManager(_catalog(), cfg.runtime_state_dir)


@app.command()
def serve() -> None:
    cfg = _settings()
    uvicorn.run("nexus_workspace.api:app", host=cfg.host, port=cfg.port, reload=False)


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


@app.command("engine-status")
def engine_status_legacy() -> None:
    """Compatibility alias for `nexus engine list`."""
    statuses = [_manager().process_status(spec.engine) for spec in _catalog().all()]
    typer.echo(json.dumps(statuses, indent=2))


@engine_app.command("list")
def engine_list() -> None:
    statuses = [_manager().process_status(spec.engine) for spec in _catalog().all()]
    typer.echo(json.dumps(statuses, indent=2))


@engine_app.command("status")
def engine_status(engine: EngineName) -> None:
    typer.echo(json.dumps(_manager().process_status(engine), indent=2))


@engine_app.command("start")
def engine_start(engine: EngineName) -> None:
    typer.echo(json.dumps(_manager().start(engine), indent=2))


@engine_app.command("stop")
def engine_stop(engine: EngineName) -> None:
    typer.echo(json.dumps(_manager().stop(engine), indent=2))


def _run_phase(engine: EngineName, phase: str) -> None:
    results = _manager().run_phase(engine, phase)
    for result in results:
        typer.echo(f"$ {' '.join(result['command'])}")
        typer.echo(result["output"], nl=not str(result["output"]).endswith("\n"))
    typer.echo(json.dumps({"engine": engine.value, "phase": phase, "status": "passed"}, indent=2))


@engine_app.command("install")
def engine_install(engine: EngineName) -> None:
    _run_phase(engine, "install")


@engine_app.command("build")
def engine_build(engine: EngineName) -> None:
    _run_phase(engine, "build")


@engine_app.command("test")
def engine_test(engine: EngineName) -> None:
    _run_phase(engine, "test")


@engine_app.command("adapters")
def engine_adapters() -> None:
    cfg = _settings()
    registry = AdapterRegistry(cfg, Path.cwd())
    typer.echo(
        json.dumps(
            [adapter.status().model_dump(mode="json") for adapter in registry.adapters.values()],
            indent=2,
        )
    )


if __name__ == "__main__":
    app()
