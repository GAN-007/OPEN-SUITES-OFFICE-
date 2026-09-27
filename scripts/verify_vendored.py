#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources.lock.json"
MANIFEST_PATH = ROOT / "engines" / "VENDOR_MANIFEST.json"


def run(command: list[str], *, input_text: str | None = None) -> str:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(command)}\n{proc.stderr}"
        )
    return proc.stdout.strip()


def index_entries(prefix: str) -> list[tuple[str, str, str]]:
    raw = run(["git", "ls-files", "-s", "-z", "--", prefix])
    entries: list[tuple[str, str, str]] = []
    for record in raw.split("\0"):
        if not record:
            continue
        metadata, path = record.split("\t", 1)
        mode, sha, stage = metadata.split(" ")
        if stage != "0":
            raise RuntimeError(f"Unmerged index entry: {path}")
        entries.append((mode, sha, path))
    return entries


def blob_sizes(shas: list[str]) -> dict[str, int]:
    unique = list(dict.fromkeys(shas))
    if not unique:
        return {}
    output = run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input_text="\n".join(unique) + "\n",
    )
    result: dict[str, int] = {}
    for line in output.splitlines():
        sha, object_type, size = line.split(" ", 2)
        if object_type != "blob":
            raise RuntimeError(f"Expected blob {sha}, got {object_type}")
        result[sha] = int(size)
    return result


def subtree_sha(prefix: str) -> str:
    root_tree = run(["git", "write-tree"])
    row = run(["git", "ls-tree", root_tree, "--", prefix])
    if not row:
        raise RuntimeError(f"Missing staged tree: {prefix}")
    metadata, _path = row.split("\t", 1)
    mode, object_type, sha = metadata.split(" ")
    if mode != "040000" or object_type != "tree":
        raise RuntimeError(f"{prefix} is not a normal Git tree")
    return sha


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
    if manifest.get("schema_version") != 2 or manifest.get("integrity_model") != "canonical-git-tree":
        print("FAIL vendor manifest is not using canonical-git-tree integrity", file=sys.stderr)
        return 1

    expected = {source["name"]: source for source in lock["sources"]}
    recorded = {engine["name"]: engine for engine in manifest["engines"]}
    errors: list[str] = []

    if set(expected) != set(recorded):
        fail(f"engine set mismatch: expected={sorted(expected)} recorded={sorted(recorded)}", errors)

    total_entries = 0
    total_bytes = 0
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

        entries = index_entries(source["path"])
        tree = subtree_sha(source["path"])
        sizes = blob_sizes([sha for _mode, sha, _path in entries])
        canonical_bytes = sum(sizes[sha] for _mode, sha, _path in entries)
        total_entries += len(entries)
        total_bytes += canonical_bytes

        if len(entries) != engine["tracked_entry_count"]:
            fail(
                f"{name}: tracked entry count drift "
                f"({len(entries)} != {engine['tracked_entry_count']})",
                errors,
            )
        if canonical_bytes != engine["canonical_blob_bytes"]:
            fail(
                f"{name}: canonical byte count drift "
                f"({canonical_bytes} != {engine['canonical_blob_bytes']})",
                errors,
            )
        if tree != engine["git_tree_sha"]:
            fail(f"{name}: Git tree drift ({tree} != {engine['git_tree_sha']})", errors)
        if tree != engine["expected_vendored_tree_sha"]:
            fail(
                f"{name}: vendored tree no longer matches canonical upstream tree",
                errors,
            )
        if len(entries) < 10:
            fail(f"{name}: implausibly small source tree ({len(entries)} entries)", errors)

        print(
            f"OK   {name:<18} entries={len(entries):<6} "
            f"bytes={canonical_bytes:<12} tree={tree[:16]}..."
        )

    if total_entries != manifest["tracked_entry_count"]:
        fail("manifest total tracked-entry count drift", errors)
    if total_bytes != manifest["canonical_blob_bytes"]:
        fail("manifest total canonical-byte count drift", errors)

    if (ROOT / ".gitmodules").exists():
        fail(".gitmodules still exists; runtime must not depend on external submodules", errors)

    raw = run(["git", "ls-files", "-s", "--", "engines"])
    gitlinks = [line for line in raw.splitlines() if line.startswith("160000 ")]
    if gitlinks:
        fail(f"vendored engines contain gitlinks: {gitlinks[:5]}", errors)

    legacy = run(["git", "ls-files", "--", "upstream"])
    if legacy:
        fail("legacy upstream/* entries remain tracked", errors)

    if errors:
        print(f"\n{len(errors)} vendoring error(s).", file=sys.stderr)
        return 1
    print(
        f"\nAll ten vendored engine trees are canonical: "
        f"{total_entries:,} tracked entries, {total_bytes:,} Git blob bytes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
