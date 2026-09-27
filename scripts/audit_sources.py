#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
REPORT = ROOT / "reports" / "source-audit.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_source(source: dict) -> dict:
    root = ROOT / source["path"]
    if not root.is_dir():
        raise RuntimeError(f"Missing vendored engine: {source['name']} at {source['path']}")

    extensions = collections.Counter()
    top = collections.Counter()
    file_count = 0
    total_bytes = 0
    license_files = []
    markers = collections.Counter()

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        file_count += 1
        size = path.lstat().st_size
        total_bytes += size
        top[rel.split("/", 1)[0]] += 1
        extensions[path.suffix.lower() or "(none)"] += 1
        if path.name.upper().startswith(("LICENSE", "NOTICE", "COPYING")):
            license_files.append({"path": rel, "sha256": sha256(path)})
        if size <= 2_000_000 and not path.is_symlink():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for marker in ("TODO", "FIXME", "NotImplemented"):
                markers[marker] += text.count(marker)

    return {
        "name": source["name"],
        "repository": source["repository"],
        "source_commit": source["commit"],
        "vendored_path": source["path"],
        "excluded_paths": source.get("excluded_paths", []),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "top_level_counts": dict(top.most_common()),
        "extension_counts": dict(extensions.most_common()),
        "code_markers": dict(markers),
        "license_files": license_files,
    }


def main() -> int:
    report = {
        "schema_version": 2,
        "snapshot_date": LOCK["snapshot_date"],
        "storage_model": "vendored-source-tree",
        "sources": [audit_source(source) for source in LOCK["sources"]],
    }
    report["total_files"] = sum(item["file_count"] for item in report["sources"])
    report["total_bytes"] = sum(item["total_bytes"] for item in report["sources"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT}")
    print(f"Audited {len(report['sources'])} engines, {report['total_files']:,} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
