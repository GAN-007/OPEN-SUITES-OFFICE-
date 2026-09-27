#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from verify_vendored import MANIFEST_PATH, canonical_digest, index_entries
from vendor_upstreams import load_lock


def main() -> int:
    lock = load_lock()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_name = {entry["name"]: entry for entry in manifest["engines"]}

    for source in lock["sources"]:
        name = source["name"]
        entries = index_entries(source["vendor_path"])
        if not entries:
            raise RuntimeError(
                f"{name}: no staged/committed entries found under {source['vendor_path']}"
            )
        record = by_name[name]
        record["git_file_count"] = len(entries)
        record["git_tree_sha256"] = canonical_digest(entries)

    manifest["engines"] = [by_name[source["name"]] for source in lock["sources"]]
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        "Finalized vendor.manifest.json with Git-canonical file counts and digests."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
