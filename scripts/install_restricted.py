#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install locally licensed source overlays that cannot be redistributed by Nexus."
    )
    parser.add_argument("--engine", choices=["genoffice"], required=True)
    parser.add_argument(
        "--acknowledge-license",
        action="store_true",
        help="Confirm that you have read and will comply with the component's separate license.",
    )
    args = parser.parse_args()

    if not args.acknowledge_license:
        raise SystemExit(
            "Refusing to copy restricted source without --acknowledge-license. "
            "GenOffice ee/ permits development/testing use, while production use or redistribution "
            "requires a valid enterprise agreement with Mainfunc, Inc."
        )

    source = ROOT / "upstream" / "genoffice" / "ee"
    destination = ROOT / "engines" / "genoffice" / "ee"
    if not source.exists():
        raise SystemExit(
            "Pinned GenOffice source is not initialized. Run git submodule update --init --recursive first."
        )
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    print(f"Installed local restricted overlay at {destination}")
    print("This directory is git-ignored and must not be committed or redistributed without permission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
