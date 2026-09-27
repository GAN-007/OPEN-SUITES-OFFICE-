#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources.lock.json"
MANIFEST_PATH = ROOT / "vendor.manifest.json"


def load_lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def restricted_paths(source: dict) -> tuple[Path, ...]:
    return tuple(Path(item["path"]) for item in source.get("restricted_paths", []))


def is_excluded(relative: Path, restricted: tuple[Path, ...]) -> bool:
    if ".git" in relative.parts:
        return True
    for blocked in restricted:
        if relative == blocked or blocked in relative.parents:
            return True
    return False


def digest_tree(root: Path, restricted: tuple[Path, ...] = ()) -> tuple[str, int]:
    if not root.exists():
        raise FileNotFoundError(root)

    digest = hashlib.sha256()
    count = 0
    paths = sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
    for path in paths:
        relative = path.relative_to(root)
        if is_excluded(relative, restricted):
            continue
        if path.is_dir() and not path.is_symlink():
            continue

        rel_bytes = relative.as_posix().encode("utf-8")
        if path.is_symlink():
            digest.update(b"L\0" + rel_bytes + b"\0" + os.readlink(path).encode("utf-8") + b"\0")
            count += 1
            continue

        if not path.is_file():
            continue

        executable = b"1" if path.lstat().st_mode & stat.S_IXUSR else b"0"
        digest.update(b"F\0" + rel_bytes + b"\0" + executable + b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
        count += 1
    return digest.hexdigest(), count


def copy_source(source_root: Path, vendor_root: Path, restricted: tuple[Path, ...]) -> None:
    if vendor_root.exists():
        shutil.rmtree(vendor_root)

    def ignore(directory: str, names: list[str]) -> set[str]:
        directory_path = Path(directory)
        relative_dir = directory_path.relative_to(source_root)
        ignored: set[str] = set()
        for name in names:
            relative = relative_dir / name
            if name == ".git" or is_excluded(relative, restricted):
                ignored.add(name)
        return ignored

    shutil.copytree(
        source_root,
        vendor_root,
        symlinks=True,
        copy_function=shutil.copy2,
        ignore=ignore,
    )


def vendor_source(source: dict) -> dict:
    source_root = ROOT / source["path"]
    vendor_root = ROOT / source["vendor_path"]
    restricted = restricted_paths(source)

    if not source_root.exists():
        raise RuntimeError(
            f"{source['name']}: pinned source tree is missing at {source_root}; "
            "initialize recursive submodules before vendoring"
        )

    copy_source(source_root, vendor_root, restricted)
    source_digest, source_count = digest_tree(source_root, restricted)
    vendor_digest, vendor_count = digest_tree(vendor_root)

    if source_digest != vendor_digest or source_count != vendor_count:
        raise RuntimeError(
            f"{source['name']}: vendored tree differs from the permitted source tree "
            f"(source {source_count}/{source_digest}, vendor {vendor_count}/{vendor_digest})"
        )

    return {
        "name": source["name"],
        "repository": source["repository"],
        "commit": source["commit"],
        "source_path": source["path"],
        "vendor_path": source["vendor_path"],
        "file_count": vendor_count,
        "tree_sha256": vendor_digest,
        "restricted_paths": source.get("restricted_paths", []),
        "license": source["license"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize pinned upstream source trees as in-repository vendored engines."
    )
    parser.add_argument("--engine", action="append", default=[], help="Vendor only a named engine.")
    args = parser.parse_args()

    lock = load_lock()
    selected = set(args.engine)
    known = {source["name"] for source in lock["sources"]}
    unknown = selected - known
    if unknown:
        raise SystemExit(f"Unknown engine(s): {', '.join(sorted(unknown))}")

    engines_root = ROOT / "engines"
    engines_root.mkdir(parents=True, exist_ok=True)

    entries = []
    for source in lock["sources"]:
        if selected and source["name"] not in selected:
            continue
        print(f"Vendoring {source['name']} from {source['commit']}...")
        entries.append(vendor_source(source))

    if selected and MANIFEST_PATH.exists():
        existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        by_name = {entry["name"]: entry for entry in existing.get("engines", [])}
        for entry in entries:
            by_name[entry["name"]] = entry
        entries = [by_name[name] for name in sorted(by_name)]
    else:
        entries.sort(key=lambda item: item["name"])

    manifest = {
        "schema_version": 1,
        "source_lock_schema_version": lock["schema_version"],
        "snapshot_date": lock["snapshot_date"],
        "engines": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH} with {len(entries)} vendored engine snapshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
