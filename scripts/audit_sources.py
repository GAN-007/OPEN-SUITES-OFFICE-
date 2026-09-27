#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sources.lock.json"
REPORT = ROOT / "reports" / "source-audit.json"


def run(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit_source(source: dict) -> dict:
    path = ROOT / source["path"]
    if not (path / ".git").exists():
        raise RuntimeError(f"Missing checkout for {source['name']}: {path}. Run bootstrap_sources.py first.")

    head = run(["git", "rev-parse", "HEAD"], path).strip()
    if head != source["commit"]:
        raise RuntimeError(f"Revision mismatch for {source['name']}: expected {source['commit']}, got {head}")

    tracked = [p for p in run(["git", "ls-files", "-z"], path).split("\0") if p]
    extensions = collections.Counter()
    top_level = collections.Counter()
    markers = collections.Counter()
    marker_files: dict[str, list[str]] = {"TODO": [], "FIXME": [], "NotImplemented": []}

    for rel in tracked:
        p = path / rel
        top_level[rel.split("/", 1)[0]] += 1
        suffix = Path(rel).suffix.lower() or "(none)"
        extensions[suffix] += 1
        if p.is_file() and p.stat().st_size <= 2_000_000:
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for marker in marker_files:
                count = text.count(marker)
                if count:
                    markers[marker] += count
                    if len(marker_files[marker]) < 100:
                        marker_files[marker].append(rel)

    license_files = []
    for candidate in ["LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "NOTICE.md", "THIRD_PARTY_NOTICES.md", "LICENSE_HISTORY"]:
        p = path / candidate
        if p.is_file():
            license_files.append({"path": candidate, "sha256": sha256(p)})

    return {
        "name": source["name"],
        "repository": source["repository"],
        "path": source["path"],
        "expected_commit": source["commit"],
        "actual_commit": head,
        "license_declaration": source["license"],
        "tracked_file_count": len(tracked),
        "top_level_counts": dict(top_level.most_common()),
        "extension_counts": dict(extensions.most_common()),
        "code_markers": dict(markers),
        "marker_files_sample": marker_files,
        "license_files": license_files,
        "tracked_files": tracked,
    }


def main() -> int:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "snapshot_date": lock["snapshot_date"],
        "sources": [audit_source(source) for source in lock["sources"]],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(s["tracked_file_count"] for s in report["sources"])
    print(f"Wrote {REPORT}")
    print(f"Audited {len(report['sources'])} repositories and {total:,} tracked files.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
