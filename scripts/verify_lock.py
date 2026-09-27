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


def safe_repo_path(value: str, prefix: str) -> bool:
    path = Path(value)
    return value.startswith(prefix) and ".." not in path.parts and not path.is_absolute()


def main() -> int:
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise ValueError("sources.lock.json must use schema_version 2")

    sources = data.get("sources")
    if not isinstance(sources, list) or len(sources) != 10:
        raise ValueError("sources.lock.json must contain exactly ten source definitions")

    names: set[str] = set()
    paths: set[str] = set()
    vendor_paths: set[str] = set()
    repos: set[str] = set()

    for index, source in enumerate(sources, start=1):
        required = {
            "name",
            "repository",
            "commit",
            "branch",
            "license",
            "path",
            "vendor_path",
            "restricted_paths",
        }
        missing = required - source.keys()
        if missing:
            raise ValueError(f"source #{index} is missing fields: {sorted(missing)}")

        name = source["name"]
        if name in names:
            raise ValueError(f"duplicate source name: {name}")
        names.add(name)

        source_path = source["path"]
        if source_path in paths or not safe_repo_path(source_path, "upstream/"):
            raise ValueError(f"invalid or duplicate source path: {source_path}")
        paths.add(source_path)

        vendor_path = source["vendor_path"]
        if vendor_path in vendor_paths or not safe_repo_path(vendor_path, "engines/"):
            raise ValueError(f"invalid or duplicate vendor path: {vendor_path}")
        vendor_paths.add(vendor_path)

        repository = source["repository"]
        if repository in repos:
            raise ValueError(f"duplicate repository: {repository}")
        repos.add(repository)
        parsed = urlparse(repository)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "github.com"
            or not repository.endswith(".git")
        ):
            raise ValueError(f"repository must be an HTTPS github.com .git URL: {repository}")

        if not SHA40.match(source["commit"]):
            raise ValueError(
                f"commit must be a full 40-character lowercase SHA: {source['commit']}"
            )

        restricted = source["restricted_paths"]
        if not isinstance(restricted, list):
            raise ValueError(f"{name}: restricted_paths must be a list")
        for item in restricted:
            if not isinstance(item, dict) or not item.get("path") or not item.get("reason"):
                raise ValueError(
                    f"{name}: each restricted path needs non-empty path and reason fields"
                )
            blocked = Path(item["path"])
            if blocked.is_absolute() or ".." in blocked.parts:
                raise ValueError(f"{name}: unsafe restricted path: {item['path']}")

    print(
        f"Lock valid: {len(sources)} unique repositories, revisions, "
        "source paths and vendored paths."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
