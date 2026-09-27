#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sources.lock.json"


def run(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout.strip()


def load_lock() -> dict:
    with LOCK.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def head_sha(path: Path) -> str:
    return run(["git", "rev-parse", "HEAD"], cwd=path)


def is_clean(path: Path) -> bool:
    return run(["git", "status", "--porcelain"], cwd=path) == ""


def ensure_source(source: dict, repair: bool) -> None:
    path = ROOT / source["path"]
    commit = source["commit"]
    repository = source["repository"]

    if path.exists() and not (path / ".git").exists():
        if repair:
            shutil.rmtree(path)
        else:
            raise RuntimeError(f"{path} exists but is not a Git checkout. Re-run with --repair to replace it.")

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(path)])

    if not is_clean(path):
        raise RuntimeError(f"Refusing to modify dirty checkout: {path}")

    current = head_sha(path)
    if current != commit:
        try:
            run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=path)
        except RuntimeError:
            run(["git", "fetch", "--filter=blob:none", "origin", commit], cwd=path)
        run(["git", "checkout", "--detach", commit], cwd=path)

    final = head_sha(path)
    if final != commit:
        raise RuntimeError(f"Revision mismatch for {source['name']}: expected {commit}, got {final}")
    print(f"OK  {source['name']:<18} {final}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch every Nexus upstream at the immutable revision in sources.lock.json")
    parser.add_argument("--only", action="append", default=[], help="Fetch only a named source; may be repeated")
    parser.add_argument("--repair", action="store_true", help="Replace a non-Git directory occupying a source path")
    args = parser.parse_args()

    if shutil.which("git") is None:
        raise RuntimeError("git is required but was not found in PATH")

    lock = load_lock()
    wanted = set(args.only)
    known = {s["name"] for s in lock["sources"]}
    unknown = wanted - known
    if unknown:
        raise RuntimeError("Unknown source name(s): " + ", ".join(sorted(unknown)))

    for source in lock["sources"]:
        if wanted and source["name"] not in wanted:
            continue
        ensure_source(source, args.repair)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
