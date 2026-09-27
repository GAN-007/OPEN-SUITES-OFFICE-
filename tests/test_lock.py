from __future__ import annotations

import json
from pathlib import Path


def test_source_lock_has_ten_unique_vendored_sources() -> None:
    data = json.loads(Path("sources.lock.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert data["storage_model"] == "vendored-source-tree"
    sources = data["sources"]
    assert len(sources) == 10
    assert len({item["name"] for item in sources}) == 10
    assert len({item["path"] for item in sources}) == 10
    assert len({item["commit"] for item in sources}) == 10
    assert all(len(item["commit"]) == 40 for item in sources)
    assert all(item["path"].startswith("engines/") for item in sources)
    assert all(item["legacy_submodule_path"].startswith("upstream/") for item in sources)


def test_genoffice_restricted_enterprise_tree_is_explicitly_excluded() -> None:
    data = json.loads(Path("sources.lock.json").read_text(encoding="utf-8"))
    genoffice = next(item for item in data["sources"] if item["name"] == "genoffice")
    assert "ee" in genoffice["excluded_paths"]
    assert "enterprise" in genoffice["restriction"].lower()


def test_open_webui_branding_restriction_is_recorded() -> None:
    data = json.loads(Path("sources.lock.json").read_text(encoding="utf-8"))
    open_webui = next(item for item in data["sources"] if item["name"] == "open-webui")
    assert "branding" in open_webui["restriction"].lower()
