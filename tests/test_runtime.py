from __future__ import annotations

import json
from pathlib import Path

from nexus_workspace.models import EngineName
from nexus_workspace.runtime import RuntimeCatalog


def test_runtime_catalog_registers_all_ten_engines() -> None:
    catalog = RuntimeCatalog(Path("engines.runtime.json"), Path.cwd())
    specs = catalog.all()
    assert len(specs) == 10
    assert {spec.engine for spec in specs} == set(EngineName)
    assert all(spec.root.as_posix().split("/")[-2] == "engines" for spec in specs)
    assert all(len(spec.capabilities) >= 4 for spec in specs)


def test_runtime_manifest_never_points_to_legacy_upstream_paths() -> None:
    payload = json.loads(Path("engines.runtime.json").read_text(encoding="utf-8"))
    for config in payload["engines"].values():
        assert config["path"].startswith("engines/")
        serialized = json.dumps(config)
        assert "upstream/" not in serialized
