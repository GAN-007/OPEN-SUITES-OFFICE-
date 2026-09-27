#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "upstream-tests.json"


def run(command: list[str], cwd: Path) -> int:
    print(f"[{cwd.name}] $ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=cwd).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pinned upstream install/build/test gates without altering their source")
    parser.add_argument("task", choices=["install", "build", "test"])
    parser.add_argument("--engine", action="append", default=[])
    parser.add_argument("--stop-on-failure", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    selected = set(args.engine)
    known = set(manifest["engines"])
    unknown = selected - known
    if unknown:
        raise SystemExit(f"Unknown engine(s): {', '.join(sorted(unknown))}")
    failures = []
    for name, config in manifest["engines"].items():
        if selected and name not in selected:
            continue
        cwd = ROOT / config["path"]
        if not cwd.exists():
            failures.append((name, "submodule is not initialized"))
            if args.stop_on_failure:
                break
            continue
        for command in config.get(args.task, []):
            rc = run(command, cwd)
            if rc != 0:
                failures.append((name, f"{args.task} command failed: {' '.join(command)}"))
                if args.stop_on_failure:
                    break
        if args.stop_on_failure and failures:
            break
    if failures:
        for name, error in failures:
            print(f"FAIL {name}: {error}", file=sys.stderr)
        return 1
    print(f"PASS upstream {args.task} gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
