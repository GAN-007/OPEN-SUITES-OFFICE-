#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "sources.lock.json").read_text())


def git(*args: str, cwd: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def main() -> int:
    failures = []
    for source in LOCK["sources"]:
        path = ROOT / source["path"]
        if not path.exists():
            failures.append(f"{source['name']}: missing {source['path']}")
            continue
        try:
            actual = git("rev-parse", "HEAD", cwd=path)
        except RuntimeError as exc:
            failures.append(f"{source['name']}: {exc}")
            continue
        if actual != source["commit"]:
            failures.append(f"{source['name']}: expected {source['commit']}, got {actual}")
        else:
            print(f"OK  {source['name']:<18} {actual}")
    if failures:
        print("\n".join(f"FAIL {item}" for item in failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
