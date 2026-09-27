#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sources.lock.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise ValueError("sources.lock.json schema_version must be 2")
    if data.get("storage_model") != "vendored-source-tree":
        raise ValueError("sources.lock.json must declare vendored-source-tree storage")

    sources = data.get("sources")
    if not isinstance(sources, list) or len(sources) != 10:
        raise ValueError("sources.lock.json must contain exactly ten source definitions")

    names: set[str] = set()
    paths: set[str] = set()
    repos: set[str] = set()
    commits: set[str] = set()

    for index, source in enumerate(sources, start=1):
        required = {
            "name",
            "repository",
            "commit",
            "branch",
            "license",
            "path",
            "legacy_submodule_path",
            "excluded_paths",
        }
        missing = required - source.keys()
        if missing:
            raise ValueError(f"source #{index} is missing fields: {sorted(missing)}")

        name = source["name"]
        path = source["path"]
        repository = source["repository"]
        commit = source["commit"]

        if name in names:
            raise ValueError(f"duplicate source name: {name}")
        if path in paths:
            raise ValueError(f"duplicate vendored path: {path}")
        if repository in repos:
            raise ValueError(f"duplicate repository: {repository}")
        if commit in commits:
            raise ValueError(f"duplicate pinned commit: {commit}")

        names.add(name)
        paths.add(path)
        repos.add(repository)
        commits.add(commit)

        parsed = urlparse(repository)
        if parsed.scheme != "https" or parsed.netloc != "github.com" or not repository.endswith(".git"):
            raise ValueError(f"repository must be an HTTPS github.com .git URL: {repository}")
        if not SHA40.match(commit):
            raise ValueError(f"commit must be a full lowercase 40-character SHA: {commit}")
        if not path.startswith("engines/") or ".." in Path(path).parts:
            raise ValueError(f"unsafe vendored source path: {path}")
        legacy = source["legacy_submodule_path"]
        if not legacy.startswith("upstream/") or ".." in Path(legacy).parts:
            raise ValueError(f"unsafe legacy submodule path: {legacy}")
        if not isinstance(source["excluded_paths"], list):
            raise ValueError(f"{name}: excluded_paths must be a list")
        for excluded in source["excluded_paths"]:
            if Path(excluded).is_absolute() or ".." in Path(excluded).parts:
                raise ValueError(f"{name}: unsafe excluded path: {excluded}")

    print(f"Lock valid: {len(sources)} unique vendored repositories, revisions and paths.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
