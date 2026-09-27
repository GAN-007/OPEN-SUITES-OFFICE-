#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources.lock.json"
MANIFEST_PATH = ROOT / "engines" / "VENDOR_MANIFEST.json"


def run(
    command: list[str],
    cwd: Path | None = None,
    *,
    capture: bool = False,
    input_text: str | None = None,
) -> str:
    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        input=input_text,
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


def run_bytes(command: list[str], cwd: Path, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(command)}\n"
            f"{proc.stderr.decode('utf-8', errors='replace')}"
        )
    return proc.stdout


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


def git_tree_for_checkout(checkout: Path, excluded_paths: list[str]) -> tuple[str, str]:
    original = run(["git", "rev-parse", "HEAD^{tree}"], checkout, capture=True)
    if not excluded_paths:
        return original, original
    for relative in excluded_paths:
        run(["git", "rm", "-r", "--cached", "--ignore-unmatch", "--", relative], checkout)
    expected = run(["git", "write-tree"], checkout, capture=True)
    return original, expected


def ls_index(cwd: Path, prefix: str | None = None) -> dict[str, tuple[str, str]]:
    command = ["git", "ls-files", "-s", "-z"]
    if prefix:
        command.extend(["--", prefix])
    raw = run(command, cwd, capture=True)
    result: dict[str, tuple[str, str]] = {}
    for record in raw.split("\0"):
        if not record:
            continue
        metadata, path = record.split("\t", 1)
        mode, sha, stage = metadata.split(" ")
        if stage != "0":
            raise RuntimeError(f"Unmerged index entry: {path}")
        result[path] = (mode, sha)
    return result


def import_blob(checkout: Path, sha: str) -> None:
    content = run_bytes(["git", "cat-file", "blob", sha], checkout)
    actual = run_bytes(["git", "hash-object", "-w", "--stdin"], ROOT, content).decode().strip()
    if actual != sha:
        raise RuntimeError(f"Blob import mismatch: expected {sha}, wrote {actual}")


def canonicalize_target_index(checkout: Path, source_path: str) -> int:
    source_entries = ls_index(checkout)
    target_entries = ls_index(ROOT, source_path)
    target_by_relative = {
        path[len(source_path) + 1 :]: value
        for path, value in target_entries.items()
        if path.startswith(source_path + "/")
    }

    if any(mode == "160000" for mode, _sha in source_entries.values()):
        raise RuntimeError(
            f"{source_path}: nested Git submodule entries require explicit flattening support"
        )

    corrections = 0
    for relative in sorted(set(target_by_relative) - set(source_entries)):
        run(["git", "update-index", "--force-remove", "--", f"{source_path}/{relative}"], ROOT)
        corrections += 1

    for relative, (mode, expected_sha) in source_entries.items():
        target = f"{source_path}/{relative}"
        current = target_by_relative.get(relative)
        if current == (mode, expected_sha):
            continue
        import_blob(checkout, expected_sha)
        run(
            ["git", "update-index", "--add", "--cacheinfo", f"{mode},{expected_sha},{target}"],
            ROOT,
        )
        corrections += 1

    return corrections


def index_entries(prefix: str) -> list[tuple[str, str, str]]:
    entries = ls_index(ROOT, prefix)
    return [(mode, sha, path) for path, (mode, sha) in entries.items()]


def blob_sizes(shas: list[str]) -> dict[str, int]:
    unique = list(dict.fromkeys(shas))
    if not unique:
        return {}
    output = run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        ROOT,
        capture=True,
        input_text="\n".join(unique) + "\n",
    )
    sizes: dict[str, int] = {}
    for line in output.splitlines():
        sha, object_type, size = line.split(" ", 2)
        if object_type != "blob":
            raise RuntimeError(f"Expected blob {sha}, got {object_type}")
        sizes[sha] = int(size)
    return sizes


def target_subtree_sha(prefix: str) -> str:
    root_tree = run(["git", "write-tree"], ROOT, capture=True)
    row = run(["git", "ls-tree", root_tree, "--", prefix], ROOT, capture=True)
    if not row:
        raise RuntimeError(f"Unable to resolve staged tree for {prefix}")
    metadata, _path = row.split("\t", 1)
    mode, object_type, sha = metadata.split(" ")
    if mode != "040000" or object_type != "tree":
        raise RuntimeError(f"{prefix} is not staged as a normal Git tree")
    return sha


def remove_legacy_gitlinks(lock: dict) -> None:
    if (ROOT / ".gitmodules").exists():
        run(["git", "rm", "-f", ".gitmodules"], ROOT)
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
            run(["git", "rm", "-f", legacy], ROOT)
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
    parser.add_argument("--keep-legacy-submodules", action="store_true")
    args = parser.parse_args()

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    sources = lock.get("sources")
    if not isinstance(sources, list) or len(sources) != 10:
        raise RuntimeError("sources.lock.json must contain exactly ten engines")

    subprocess.run(
        ["git", "rm", "-r", "-f", "--cached", "--ignore-unmatch", "engines"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    engines_root = ROOT / "engines"
    if engines_root.exists():
        shutil.rmtree(engines_root)
    engines_root.mkdir(parents=True)

    provisional: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="nexus-vendor-") as temp:
        scratch = Path(temp)
        for source in sources:
            name = source["name"]
            repository = source["repository"]
            commit = source["commit"]
            destination = ROOT / source["path"]
            clone = scratch / name

            print(f"==> {name}: cloning {repository}")
            run(["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(clone)])
            try:
                run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], clone, capture=True)
            except RuntimeError:
                run(["git", "fetch", "--depth", "1", "origin", commit], clone)
            run(
                ["git", "-c", "advice.detachedHead=false", "checkout", "--detach", commit],
                clone,
            )
            actual = run(["git", "rev-parse", "HEAD"], clone, capture=True)
            if actual != commit:
                raise RuntimeError(f"{name}: expected {commit}, checked out {actual}")

            nested_submodules = False
            if (clone / ".gitmodules").exists():
                nested_submodules = True
                run(["git", "submodule", "sync", "--recursive"], clone)
                run(["git", "submodule", "update", "--init", "--recursive"], clone)

            excluded = list(source.get("excluded_paths", []))
            original_tree, expected_tree = git_tree_for_checkout(clone, excluded)

            print(f"==> {name}: copying source into {destination.relative_to(ROOT)}")
            copy_worktree(clone, destination)
            remove_excluded_paths(destination, excluded)

            provisional.append(
                {
                    "name": name,
                    "source_repository": repository,
                    "source_commit": commit,
                    "source_tree_sha": original_tree,
                    "expected_vendored_tree_sha": expected_tree,
                    "vendored_path": source["path"],
                    "license": source["license"],
                    "excluded_paths": excluded,
                    "restriction": source.get("restriction"),
                    "nested_submodules_materialized": nested_submodules,
                    "_checkout": clone,
                }
            )

        if not args.keep_legacy_submodules:
            remove_legacy_gitlinks(lock)

        run(["git", "add", "-A"], ROOT)
        run(["git", "add", "-f", "--", "engines"], ROOT)

        for item in provisional:
            corrections = canonicalize_target_index(item["_checkout"], item["vendored_path"])
            item["canonical_index_corrections"] = corrections
            print(f"==> {item['name']}: canonical index corrections={corrections}")

        results: list[dict] = []
        for item in provisional:
            checkout = item.pop("_checkout")
            del checkout
            prefix = item["vendored_path"]
            entries = index_entries(prefix)
            subtree = target_subtree_sha(prefix)
            if subtree != item["expected_vendored_tree_sha"]:
                raise RuntimeError(
                    f"{item['name']}: canonicalized Git tree {subtree} does not match "
                    f"upstream {item['expected_vendored_tree_sha']}"
                )
            sizes = blob_sizes([sha for _mode, sha, _path in entries])
            results.append(
                {
                    **item,
                    "git_tree_sha": subtree,
                    "tracked_entry_count": len(entries),
                    "canonical_blob_bytes": sum(
                        sizes[sha] for _mode, sha, _path in entries
                    ),
                }
            )

    manifest = {
        "schema_version": 2,
        "snapshot_date": lock["snapshot_date"],
        "storage_model": "vendored-source-tree",
        "integrity_model": "canonical-git-tree",
        "engine_count": len(results),
        "tracked_entry_count": sum(item["tracked_entry_count"] for item in results),
        "canonical_blob_bytes": sum(item["canonical_blob_bytes"] for item in results),
        "engines": results,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    run(["git", "add", "-f", "--", str(MANIFEST_PATH.relative_to(ROOT))], ROOT)

    print("\nVendored engine summary")
    for item in results:
        print(
            f"  {item['name']:<18} entries={item['tracked_entry_count']:<6} "
            f"bytes={item['canonical_blob_bytes']:<12} tree={item['git_tree_sha'][:16]}..."
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
