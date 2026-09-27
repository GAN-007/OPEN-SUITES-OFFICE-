#!/usr/bin/env python3
"""Compatibility entrypoint for the former submodule verifier.

The runtime source-of-truth is now the vendored engines/* tree.
"""
from verify_vendored import main

if __name__ == "__main__":
    raise SystemExit(main())
