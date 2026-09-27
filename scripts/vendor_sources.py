#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources.lock.json"
MANIFEST_PATH = ROOT / "engines" / "VENDOR_MANIFEST.json"


def run(command: list[str], cwd: Path | None = None, *, capture: bool = False) -> str:
    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if proc.returncode != 0:
        details = ""
        if capture:
            details = f"\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(command)}{details}")
    return proc.stdout.strip() if capture else ""


def remove_git_metadata(root: Path) -> None:
    for path in sorted(root.rglob(".git"), reverse=True):
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)


def copy_worktree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name == ".git"}

    shutil.copytree(source, destination, symlinks=True, ignore=ignore)
    remove_git_metadata(destination)


def remove_excluded_paths(destination: Path, excluded_paths: list[str]) -> None:
    for relative in excluded_paths:
        target = destination / relative
        if not target.exists() and not target.is_symlink():
            continue
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()


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


def tree_fingerprint(root: Path) -> dict:
    aggregate = hashlib.sha256()
    count = 0
    total_bytes = 0
    largest: list[tuple[int, str]] = []

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
        largest.append((size, relative))

    largest.sort(reverse=True)
    return {
        "file_count": count,
        "total_bytes": total_bytes,
        "aggregate_sha256": aggregate.hexdigest(),
        "largest_files": [{"path": path, "bytes": size} for size, path in largest[:20]],
    }


def materialize_source(source: dict, scratch: Path) -> dict:
    name = source["name"]
    repository = source["repository"]
    commit = source["commit"]
    destination = ROOT / source["path"]
    clone = scratch / name

    print(f"==> {name}: cloning {repository}")
    run(["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(clone)])
    try:
        run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=clone, capture=True)
    except RuntimeError:
        run(["git", "fetch", "--depth", "1", "origin", commit], cwd=clone)

    run(["git", "-c", "advice.detachedHead=false", "checkout", "--detach", commit], cwd=clone)
    actual = run(["git", "rev-parse", "HEAD"], cwd=clone, capture=True)
    if actual != commit:
        raise RuntimeError(f"{name}: expected {commit}, checked out {actual}")

    gitmodules = clone / ".gitmodules"
    nested_submodules = False
    if gitmodules.exists():
        nested_submodules = True
        print(f"==> {name}: materializing nested submodules")
        run(["git", "submodule", "sync", "--recursive"], cwd=clone)
        run(["git", "submodule", "update", "--init", "--recursive"], cwd=clone)

    print(f"==> {name}: copying source into {destination.relative_to(ROOT)}")
    copy_worktree(clone, destination)

    excluded = list(source.get("excluded_paths", []))
    remove_excluded_paths(destination, excluded)

    if not (destination / "LICENSE").exists() and not (destination / "LICENSE.md").exists():
        print(f"WARNING: {name} has no root LICENSE file at the vendored destination", file=sys.stderr)

    fingerprint = tree_fingerprint(destination)
    return {
        "name": name,
        "source_repository": repository,
        "source_commit": commit,
        "vendored_path": source["path"],
        "license": source["license"],
        "excluded_paths": excluded,
        "restriction": source.get("restriction"),
        "nested_submodules_materialized": nested_submodules,
        **fingerprint,
    }


def remove_legacy_gitlinks(lock: dict) -> None:
    gitmodules = ROOT / ".gitmodules"
    if gitmodules.exists():
        run(["git", "rm", "-f", ".gitmodules"], cwd=ROOT)

    for source in lock["sources"]:
        legacy = source.get("legacy_submodule_path")
        if not legacy:
            continue
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", legacy],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if tracked.returncode == 0:
            run(["git", "rm", "-f", legacy], cwd=ROOT)
        else:
            path = ROOT / legacy
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vendor the exact pinned engine source trees into this repository."
    )
    parser.add_argument(
        "--keep-legacy-submodules",
        action="store_true",
        help="Do not remove the old upstream/* gitlinks after vendoring.",
    )
    args = parser.parse_args()

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    sources = lock.get("sources")
    if not isinstance(sources, list) or len(sources) != 10:
        raise RuntimeError("sources.lock.json must contain exactly ten engines")

    engines_root = ROOT / "engines"
    if engines_root.exists():
        for child in engines_root.iterdir():
            if child.name == "VENDOR_MANIFEST.json":
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        engines_root.mkdir(parents=True)

    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="nexus-vendor-") as temp:
        scratch = Path(temp)
        for source in sources:
            results.append(materialize_source(source, scratch))

    manifest = {
        "schema_version": 1,
        "snapshot_date": lock["snapshot_date"],
        "storage_model": "vendored-source-tree",
        "engine_count": len(results),
        "engines": results,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if not args.keep_legacy_submodules:
        remove_legacy_gitlinks(lock)

    print("\nVendored engine summary")
    for item in results:
        print(
            f"  {item['name']:<18} files={item['file_count']:<6} "
            f"bytes={item['total_bytes']:<12} sha256={item['aggregate_sha256'][:16]}..."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
