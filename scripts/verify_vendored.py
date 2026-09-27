#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources.lock.json"
MANIFEST_PATH = ROOT / "engines" / "VENDOR_MANIFEST.json"


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(b"SYMLINK\0")
        digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        return digest.hexdigest()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(root: Path) -> tuple[int, int, str]:
    aggregate = hashlib.sha256()
    count = 0
    total_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_dir() and not path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        digest = file_digest(path)
        mode = stat.S_IMODE(path.lstat().st_mode)
        size = path.lstat().st_size if not path.is_symlink() else len(os.readlink(path).encode())
        aggregate.update(relative.encode("utf-8", errors="surrogateescape"))
        aggregate.update(b"\0")
        aggregate.update(f"{mode:o}".encode())
        aggregate.update(b"\0")
        aggregate.update(str(size).encode())
        aggregate.update(b"\0")
        aggregate.update(digest.encode())
        aggregate.update(b"\n")
        count += 1
        total_bytes += size
    return count, total_bytes, aggregate.hexdigest()


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)
    print(f"FAIL {message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify every vendored Nexus engine tree.")
    parser.add_argument("--require", action="store_true", help="Fail if vendored sources are absent.")
    args = parser.parse_args()

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if not MANIFEST_PATH.exists():
        if args.require:
            print("FAIL engines/VENDOR_MANIFEST.json is missing", file=sys.stderr)
            return 1
        print("Vendored sources are not present; verification skipped.")
        return 0

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = {source["name"]: source for source in lock["sources"]}
    recorded = {engine["name"]: engine for engine in manifest["engines"]}
    errors: list[str] = []

    if set(expected) != set(recorded):
        fail(f"engine set mismatch: expected={sorted(expected)} recorded={sorted(recorded)}", errors)

    for name, source in expected.items():
        engine = recorded.get(name)
        if engine is None:
            continue
        root = ROOT / source["path"]
        if not root.is_dir():
            fail(f"{name}: missing vendored directory {source['path']}", errors)
            continue
        if engine["source_commit"] != source["commit"]:
            fail(f"{name}: manifest source commit mismatch", errors)
        for excluded in source.get("excluded_paths", []):
            if (root / excluded).exists():
                fail(f"{name}: restricted/excluded path unexpectedly vendored: {excluded}", errors)

        count, total_bytes, digest = fingerprint(root)
        if count != engine["file_count"]:
            fail(f"{name}: file count drift ({count} != {engine['file_count']})", errors)
        if total_bytes != engine["total_bytes"]:
            fail(f"{name}: byte count drift ({total_bytes} != {engine['total_bytes']})", errors)
        if digest != engine["aggregate_sha256"]:
            fail(f"{name}: aggregate SHA-256 drift", errors)
        if count < 10:
            fail(f"{name}: implausibly small source tree ({count} files)", errors)
        print(f"OK   {name:<18} files={count:<6} sha256={digest[:16]}...")

    if (ROOT / ".gitmodules").exists():
        fail(".gitmodules still exists; runtime must not depend on external submodules", errors)

    proc = subprocess.run(
        ["git", "ls-files", "-s", "engines"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        fail(f"unable to inspect Git index: {proc.stderr.strip()}", errors)
    else:
        gitlinks = [line for line in proc.stdout.splitlines() if line.startswith("160000 ")]
        if gitlinks:
            fail(f"vendored engines contain gitlinks: {gitlinks[:5]}", errors)

    legacy = subprocess.run(
        ["git", "ls-files", "upstream"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if legacy.stdout.strip():
        fail("legacy upstream/* entries remain tracked", errors)

    if errors:
        print(f"\n{len(errors)} vendoring error(s).", file=sys.stderr)
        return 1
    print("\nAll ten vendored engine trees are present and integrity-verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
