#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from vendor_upstreams import MANIFEST_PATH, ROOT, load_lock, restricted_paths


def git(*args: str, cwd: Path = ROOT, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd}: "
            f"{proc.stderr.decode('utf-8', errors='replace')}"
        )
    return proc.stdout


def index_entries(prefix: str) -> dict[str, tuple[str, str]]:
    raw = git("ls-files", "-s", "-z", "--", prefix)
    result: dict[str, tuple[str, str]] = {}
    marker = prefix.rstrip("/") + "/"
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, path_bytes = record.split(b"\t", 1)
        mode_b, sha_b, stage_b = header.split(b" ", 2)
        if stage_b != b"0":
            raise RuntimeError(f"Unmerged index entry under {prefix}")
        path = path_bytes.decode("utf-8", errors="surrogateescape")
        if not path.startswith(marker):
            continue
        relative = path[len(marker):]
        result[relative] = (mode_b.decode(), sha_b.decode())
    return result


def canonical_digest(entries: dict[str, tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for path in sorted(entries):
        mode, blob_sha = entries[path]
        digest.update(mode.encode("ascii"))
        digest.update(b"\0")
        digest.update(path.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(blob_sha.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def source_clean_entries(source: dict) -> dict[str, tuple[str, str]]:
    source_root = ROOT / source["path"]
    if not source_root.exists():
        raise RuntimeError(f"{source['name']}: source checkout missing at {source_root}")

    blocked = restricted_paths(source)
    raw = git("ls-files", "-s", "-z", cwd=source_root)
    result: dict[str, tuple[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, path_bytes = record.split(b"\t", 1)
        mode_b, _sha_b, stage_b = header.split(b" ", 2)
        if stage_b != b"0":
            continue
        relative = path_bytes.decode("utf-8", errors="surrogateescape")
        rel_path = Path(relative)
        if any(rel_path == item or item in rel_path.parents for item in blocked):
            continue

        mode = mode_b.decode()
        if mode == "160000":
            raise RuntimeError(
                f"{source['name']}: nested gitlink {relative} requires explicit vendoring support"
            )
        if mode == "120000":
            clean_sha = git("rev-parse", f"HEAD:{relative}", cwd=source_root).decode().strip()
        else:
            clean_sha = git(
                "hash-object",
                f"--path={relative}",
                relative,
                cwd=source_root,
            ).decode().strip()
        result[relative] = (mode, clean_sha)
    return result


def compare_source_to_vendor(source: dict, vendor_entries: dict[str, tuple[str, str]]) -> None:
    expected = source_clean_entries(source)
    if expected == vendor_entries:
        return

    paths = sorted(set(expected) | set(vendor_entries))
    diffs = []
    for path in paths:
        left = expected.get(path)
        right = vendor_entries.get(path)
        if left != right:
            diffs.append((path, left, right))
        if len(diffs) >= 20:
            break
    detail = "\n".join(
        f"  {path}: source={left!r} vendor={right!r}" for path, left, right in diffs
    )
    raise RuntimeError(
        f"{source['name']}: canonical source/vendor Git parity failed\n{detail}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify committed vendored engine snapshots using Git-canonical blobs and modes."
    )
    parser.add_argument(
        "--compare-sources",
        action="store_true",
        help="Also compare vendor index entries with the initialized pinned sources after applying their Git clean filters.",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        raise RuntimeError("vendor.manifest.json is missing")

    lock = load_lock()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    locked = {source["name"]: source for source in lock["sources"]}
    entries = {entry["name"]: entry for entry in manifest.get("engines", [])}

    if set(entries) != set(locked):
        missing = sorted(set(locked) - set(entries))
        extra = sorted(set(entries) - set(locked))
        raise RuntimeError(f"Vendored engine set mismatch; missing={missing}, extra={extra}")

    total_files = 0
    for name in sorted(locked):
        source = locked[name]
        entry = entries[name]
        vendor_root = ROOT / source["vendor_path"]
        if not vendor_root.is_dir():
            raise RuntimeError(f"{name}: vendored source tree missing at {vendor_root}")
        if entry["commit"] != source["commit"]:
            raise RuntimeError(f"{name}: vendor commit does not match source lock")
        if entry["vendor_path"] != source["vendor_path"]:
            raise RuntimeError(f"{name}: vendor path does not match source lock")

        for restricted in source.get("restricted_paths", []):
            blocked = vendor_root / restricted["path"]
            if blocked.exists():
                raise RuntimeError(
                    f"{name}: restricted path was redistributed into the vendored tree: {blocked}"
                )

        vendor_entries = index_entries(source["vendor_path"])
        digest = canonical_digest(vendor_entries)
        expected_digest = entry.get("git_tree_sha256")
        expected_count = entry.get("git_file_count")

        if expected_digest is None or expected_count is None:
            raise RuntimeError(
                f"{name}: vendor.manifest.json lacks finalized Git-canonical fields"
            )
        if digest != expected_digest or len(vendor_entries) != expected_count:
            raise RuntimeError(
                f"{name}: committed vendor Git tree changed "
                f"(expected {expected_count}/{expected_digest}, "
                f"got {len(vendor_entries)}/{digest})"
            )

        if args.compare_sources:
            compare_source_to_vendor(source, vendor_entries)

        total_files += len(vendor_entries)
        print(f"OK  {name:<18} {len(vendor_entries):>6} files  {digest}")

    print(
        f"Verified {len(entries)} vendored engines and {total_files:,} "
        "Git-canonical permitted files."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
