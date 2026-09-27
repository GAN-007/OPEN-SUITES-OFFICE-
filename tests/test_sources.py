from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_workspace.models import EngineName
from nexus_workspace.source_resolver import EngineSourceMissing, EngineSourceResolver


ROOT = Path(__file__).resolve().parents[1]


def test_vendor_manifest_contains_all_ten_engines() -> None:
    manifest = json.loads((ROOT / "vendor.manifest.json").read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in manifest["engines"]}
    assert entries.keys() == {engine.value for engine in EngineName}
    for entry in entries.values():
        assert (ROOT / entry["vendor_path"]).is_dir()
        assert entry["file_count"] > 0
        assert len(entry["tree_sha256"]) == 64
        assert entry["git_file_count"] > 0
        assert len(entry["git_tree_sha256"]) == 64


def test_runtime_defaults_to_vendored_source() -> None:
    resolver = EngineSourceResolver(ROOT, mode="vendored")
    for engine in EngineName:
        path = resolver.resolve(engine)
        assert path == ROOT / "engines" / engine.value
        assert path.is_dir()


def test_genoffice_enterprise_directory_is_not_redistributed() -> None:
    assert not (ROOT / "engines" / "genoffice" / "ee").exists()


def test_missing_vendored_tree_fails_closed(tmp_path: Path) -> None:
    resolver = EngineSourceResolver(tmp_path, mode="vendored")
    with pytest.raises(EngineSourceMissing):
        resolver.resolve(EngineName.GENOFFICE)
