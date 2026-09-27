#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "engines.runtime.json").read_text(encoding="utf-8"))


def run(command: list[str], cwd: Path) -> int:
    print(f"[{cwd.name}] $ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=cwd).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run native install/build/test gates against vendored engines."
    )
    parser.add_argument("task", choices=["install", "build", "test"])
    parser.add_argument("--engine", action="append", default=[])
    parser.add_argument("--stop-on-failure", action="store_true")
    args = parser.parse_args()

    selected = set(args.engine)
    known = set(MANIFEST["engines"])
    unknown = selected - known
    if unknown:
        raise SystemExit(f"Unknown engine(s): {', '.join(sorted(unknown))}")

    failures: list[tuple[str, str]] = []
    for name, config in MANIFEST["engines"].items():
        if selected and name not in selected:
            continue
        cwd = ROOT / config["path"]
        if not cwd.is_dir():
            failures.append((name, f"vendored path missing: {cwd}"))
            if args.stop_on_failure:
                break
            continue
        commands = config.get(args.task, [])
        for command in commands:
            rc = run(command, cwd)
            if rc != 0:
                failures.append((name, f"{args.task} command failed: {' '.join(command)}"))
                if args.stop_on_failure:
                    break
        if args.stop_on_failure and failures:
            break

    if failures:
        for name, reason in failures:
            print(f"FAIL {name}: {reason}", file=sys.stderr)
        return 1
    print(f"PASS vendored engine {args.task} gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
