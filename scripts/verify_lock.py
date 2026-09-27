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
    sources = data.get("sources")
    if not isinstance(sources, list) or len(sources) != 10:
        raise ValueError("sources.lock.json must contain exactly ten source definitions")

    names: set[str] = set()
    paths: set[str] = set()
    repos: set[str] = set()
    for index, source in enumerate(sources, start=1):
        required = {"name", "repository", "commit", "branch", "license", "path"}
        missing = required - source.keys()
        if missing:
            raise ValueError(f"source #{index} is missing fields: {sorted(missing)}")
        name = source["name"]
        if name in names:
            raise ValueError(f"duplicate source name: {name}")
        names.add(name)
        path = source["path"]
        if path in paths:
            raise ValueError(f"duplicate source path: {path}")
        paths.add(path)
        repository = source["repository"]
        if repository in repos:
            raise ValueError(f"duplicate repository: {repository}")
        repos.add(repository)
        parsed = urlparse(repository)
        if parsed.scheme != "https" or parsed.netloc != "github.com" or not repository.endswith(".git"):
            raise ValueError(f"repository must be an HTTPS github.com .git URL: {repository}")
        if not SHA40.match(source["commit"]):
            raise ValueError(f"commit must be a full 40-character lowercase SHA: {source['commit']}")
        if not path.startswith("upstream/") or ".." in Path(path).parts:
            raise ValueError(f"unsafe source path: {path}")

    print(f"Lock valid: {len(sources)} unique repositories, revisions and paths.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
