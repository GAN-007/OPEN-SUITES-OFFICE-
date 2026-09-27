#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vendor_upstreams import ROOT, MANIFEST_PATH, digest_tree, load_lock, restricted_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify committed vendored engine snapshots.")
    parser.add_argument(
        "--compare-sources",
        action="store_true",
        help="Also compare vendored trees against initialized pinned source trees.",
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

        vendor_digest, vendor_count = digest_tree(vendor_root)
        if vendor_digest != entry["tree_sha256"] or vendor_count != entry["file_count"]:
            raise RuntimeError(
                f"{name}: committed vendor tree changed "
                f"(expected {entry['file_count']}/{entry['tree_sha256']}, "
                f"got {vendor_count}/{vendor_digest})"
            )

        if args.compare_sources:
            source_root = ROOT / source["path"]
            if not source_root.exists():
                raise RuntimeError(f"{name}: source checkout missing at {source_root}")
            source_digest, source_count = digest_tree(source_root, restricted_paths(source))
            if (source_digest, source_count) != (vendor_digest, vendor_count):
                raise RuntimeError(
                    f"{name}: vendor/source parity failed "
                    f"(source {source_count}/{source_digest}, vendor {vendor_count}/{vendor_digest})"
                )

        total_files += vendor_count
        print(f"OK  {name:<18} {vendor_count:>6} files  {vendor_digest}")

    print(f"Verified {len(entries)} vendored engines and {total_files:,} permitted files.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
