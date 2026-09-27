from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import EngineName


@dataclass(frozen=True)
class RuntimeSpec:
    engine: EngineName
    root: Path
    kind: str
    install: list[list[str]]
    build: list[list[str]]
    test: list[list[str]]
    start: list[str] | None
    cli: list[str] | None
    env: dict[str, str]
    capabilities: list[str]


class RuntimeCatalog:
    def __init__(self, manifest_path: Path, repository_root: Path | None = None):
        self.repository_root = (repository_root or Path.cwd()).resolve()
        self.manifest_path = (
            manifest_path if manifest_path.is_absolute() else self.repository_root / manifest_path
        )
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 2:
            raise ValueError("engines.runtime.json schema_version must be 2")
        engines = payload.get("engines")
        if not isinstance(engines, dict):
            raise ValueError("engines.runtime.json must contain an engines object")
        self._raw: dict[str, dict[str, Any]] = engines

    @staticmethod
    def _resolve_command(root: Path, command: list[str] | None) -> list[str] | None:
        if not command:
            return None
        resolved: list[str] = []
        for value in command:
            candidate = root / value
            if (
                "/" in value
                and not value.startswith("-")
                and not Path(value).is_absolute()
                and candidate.exists()
            ):
                resolved.append(str(candidate))
            else:
                resolved.append(value)
        return resolved

    def spec(self, engine: EngineName) -> RuntimeSpec:
        raw = self._raw[engine.value]
        root = (self.repository_root / raw["path"]).resolve()
        return RuntimeSpec(
            engine=engine,
            root=root,
            kind=str(raw.get("kind", "native")),
            install=[list(item) for item in raw.get("install", [])],
            build=[list(item) for item in raw.get("build", [])],
            test=[list(item) for item in raw.get("test", [])],
            start=self._resolve_command(root, raw.get("start")),
            cli=self._resolve_command(root, raw.get("cli")),
            env={str(key): str(value) for key, value in raw.get("env", {}).items()},
            capabilities=list(raw.get("capabilities", [])),
        )

    def all(self) -> list[RuntimeSpec]:
        return [self.spec(engine) for engine in EngineName]

    def status(self, engine: EngineName) -> dict[str, Any]:
        spec = self.spec(engine)
        return {
            "engine": engine.value,
            "kind": spec.kind,
            "path": str(spec.root),
            "source_present": spec.root.is_dir(),
            "capabilities": spec.capabilities,
            "cli": spec.cli,
            "start": spec.start,
            "env": spec.env,
            "install_commands": spec.install,
            "build_commands": spec.build,
            "test_commands": spec.test,
        }


class NativeProcessManager:
    def __init__(self, catalog: RuntimeCatalog, state_dir: Path):
        self.catalog = catalog
        self.state_dir = state_dir.resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = self.state_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _state_file(self, engine: EngineName) -> Path:
        return self.state_dir / f"{engine.value}.json"

    def _read_state(self, engine: EngineName) -> dict[str, Any] | None:
        path = self._state_file(engine)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def _environment(spec: RuntimeSpec) -> dict[str, str]:
        env = os.environ.copy()
        env.update(spec.env)
        return env

    def process_status(self, engine: EngineName) -> dict[str, Any]:
        state = self._read_state(engine)
        running = bool(state and self._pid_alive(int(state["pid"])))
        if state and not running:
            self._state_file(engine).unlink(missing_ok=True)
        return {
            **self.catalog.status(engine),
            "running": running,
            "pid": int(state["pid"]) if running and state else None,
            "log": state.get("log") if running and state else None,
        }

    def run_phase(self, engine: EngineName, phase: str) -> list[dict[str, Any]]:
        if phase not in {"install", "build", "test"}:
            raise ValueError(f"Unsupported runtime phase: {phase}")
        spec = self.catalog.spec(engine)
        if not spec.root.is_dir():
            raise FileNotFoundError(f"Vendored source missing: {spec.root}")
        commands: list[list[str]] = getattr(spec, phase)
        results: list[dict[str, Any]] = []
        for command in commands:
            proc = subprocess.run(
                command,
                cwd=spec.root,
                env=self._environment(spec),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            result = {
                "command": command,
                "returncode": proc.returncode,
                "output": proc.stdout,
            }
            results.append(result)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"{engine.value} {phase} failed ({proc.returncode}): "
                    f"{' '.join(command)}\n{proc.stdout}"
                )
        return results

    def start(self, engine: EngineName) -> dict[str, Any]:
        current = self.process_status(engine)
        if current["running"]:
            return current
        spec = self.catalog.spec(engine)
        if not spec.start:
            raise ValueError(f"{engine.value} does not expose a long-running native start command")
        if not spec.root.is_dir():
            raise FileNotFoundError(f"Vendored source missing: {spec.root}")

        log_path = self.log_dir / f"{engine.value}.log"
        log_handle = log_path.open("ab", buffering=0)
        try:
            process = subprocess.Popen(
                spec.start,
                cwd=spec.root,
                env=self._environment(spec),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        finally:
            log_handle.close()

        state = {
            "pid": process.pid,
            "command": spec.start,
            "cwd": str(spec.root),
            "env": spec.env,
            "log": str(log_path),
        }
        self._state_file(engine).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return self.process_status(engine)

    def stop(self, engine: EngineName) -> dict[str, Any]:
        state = self._read_state(engine)
        if not state:
            return self.process_status(engine)
        pid = int(state["pid"])
        if self._pid_alive(pid):
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        self._state_file(engine).unlink(missing_ok=True)
        return self.process_status(engine)
