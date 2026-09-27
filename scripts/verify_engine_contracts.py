#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = json.loads((ROOT / "engines.runtime.json").read_text(encoding="utf-8"))

CONTRACTS: dict[str, list[list[str]]] = {
    "genoffice": [
        ["package.json"],
        ["apps/docs"],
        ["apps/sheets"],
        ["apps/slides"],
        ["apps/pdf"],
        ["apps/markdown"],
        ["apps/html"],
        ["packages/agent-core"],
        ["packages/cli"],
    ],
    "openmaic": [
        ["package.json"],
        ["app"],
        ["components"],
        ["lib"],
        ["packages"],
        ["skills"],
        ["tests"],
    ],
    "weknora": [
        ["go.mod"],
        ["cmd"],
        ["internal"],
        ["frontend"],
        ["mcp-server"],
        ["migrations"],
        ["tests"],
    ],
    "graphiti": [
        ["pyproject.toml"],
        ["graphiti_core"],
        ["mcp_server"],
        ["server"],
        ["tests"],
    ],
    "cognee": [
        ["pyproject.toml"],
        ["cognee"],
        ["cognee-mcp"],
        ["cognee-frontend"],
        ["evals"],
        ["tests"],
    ],
    "browser-use": [
        ["pyproject.toml"],
        ["browser_use"],
        ["skills"],
        ["tests"],
    ],
    "open-webui": [
        ["package.json"],
        ["pyproject.toml"],
        ["backend"],
        ["src"],
        ["static"],
        ["test"],
    ],
    "pageindex": [
        ["pyproject.toml"],
        ["pageindex"],
        ["examples"],
        ["tests"],
    ],
    "agent-reach": [
        ["pyproject.toml"],
        ["agent_reach"],
        ["config"],
        ["tests"],
    ],
    "qwen-audio-agent": [
        ["package.json"],
        ["server"],
        ["cli"],
        ["web"],
        ["desktop"],
        ["mobile"],
        ["shared"],
        ["test"],
    ],
}


def main() -> int:
    errors: list[str] = []
    runtime_engines = RUNTIME.get("engines", {})
    if set(runtime_engines) != set(CONTRACTS):
        errors.append(
            f"runtime/contract engine mismatch: runtime={sorted(runtime_engines)} "
            f"contracts={sorted(CONTRACTS)}"
        )

    for name, alternatives in CONTRACTS.items():
        config = runtime_engines.get(name)
        if not config:
            continue
        root = ROOT / config["path"]
        missing: list[str] = []
        for candidates in alternatives:
            if not any((root / candidate).exists() for candidate in candidates):
                missing.append(" | ".join(candidates))
        if missing:
            errors.append(f"{name}: missing capability roots: {', '.join(missing)}")
            continue

        capabilities = config.get("capabilities", [])
        if len(capabilities) < 4:
            errors.append(f"{name}: capability registry is unexpectedly sparse")
            continue
        print(f"OK   {name:<18} capability_roots={len(alternatives):<2} capabilities={len(capabilities)}")

    genoffice_ee = ROOT / "engines/genoffice/ee"
    if genoffice_ee.exists():
        errors.append("genoffice: restricted ee/ directory must not be publicly vendored")

    ow_license = ROOT / "engines/open-webui/LICENSE"
    if ow_license.exists():
        text = ow_license.read_text(encoding="utf-8", errors="replace")
        if "branding" not in text.lower() or "Open WebUI" not in text:
            errors.append("open-webui: expected branding-preservation license text is missing")
    else:
        errors.append("open-webui: LICENSE is missing")

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print("\nAll engine capability-root contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
