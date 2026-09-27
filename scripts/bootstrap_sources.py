#!/usr/bin/env python3
"""Compatibility entrypoint for the old bootstrap command.

Nexus no longer materializes runtime code as Git submodules. This command now
vendors the pinned source trees into engines/*.
"""
from vendor_sources import main

if __name__ == "__main__":
    raise SystemExit(main())
