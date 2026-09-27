# OPEN SUITES OFFICE — Nexus

**One repository. Ten specialist AI engines. One control plane.**

Nexus 0.2 is no longer a submodule federation. The redistributable source code
for GenOffice, OpenMAIC, WeKnora, Graphiti, Cognee, Browser Use, Open WebUI,
PageIndex, Agent-Reach, and Qwen Audio Agent is vendored directly under
`engines/` at immutable audited revisions. Nexus routes, starts, tests, and
invokes those in-repository implementations through a common API and CLI while
preserving each engine's native UI, CLI, SDK, MCP/ACP/A2A interfaces, database
model, test suite, and license boundary.

## What “in-house” means here

A normal clone contains the implementation source itself:

```text
engines/
├── genoffice/
├── openmaic/
├── weknora/
├── graphiti/
├── cognee/
├── browser-use/
├── open-webui/
├── pageindex/
├── agent-reach/
└── qwen-audio-agent/
```

There is no runtime requirement to initialize `upstream/*` submodules or
download those repositories before Nexus can inspect, build, test, or invoke
their code.

The exact source commit, redistribution boundary, and original repository for
each engine are recorded in `sources.lock.json`; integrity fingerprints are in
`engines/VENDOR_MANIFEST.json`.

## Capability ownership

| Engine | In-repository capabilities retained |
|---|---|
| **GenOffice** | Docs, Sheets, Slides, PDF, Markdown, HTML, Office engines, AI agent core, CLI, MCP, skills, rendering/conversion pipelines |
| **OpenMAIC** | Agent workbench, generation, multi-agent orchestration, classroom playback, quizzes, PBL, whiteboards, materials, skills, PPTX/HTML export |
| **WeKnora** | Enterprise knowledge bases, document ingestion, RAG, ReAct Agent, Wiki, RBAC/workspaces, MCP, sandboxes, browser/search skills, migrations |
| **Graphiti** | Temporal knowledge graph, episodes, entities, edges, validity windows, hybrid search, graph drivers, MCP |
| **Cognee** | remember, recall, improve, forget, session memory, graph/vector/code retrieval, API, MCP, UI |
| **Browser Use** | Browser agent, navigation, clicking, typing, forms, tabs, profiles, extraction, screenshots, sessions, MCP |
| **Open WebUI** | Models, agents, tools, skills, RAG, memory, channels, calendar, automations, voice/video, image generation, analytics, RBAC, PWA |
| **PageIndex** | Hierarchical tree indexing, vectorless reasoning retrieval, local chat, Flash indexing, SDK integrations |
| **Agent-Reach** | Web read/search plus source-specific GitHub, X/Twitter, Reddit, LinkedIn, YouTube, Bilibili, RSS and diagnostic/fallback channels |
| **Qwen Audio Agent** | Full-duplex voice, interruption, background tasks, unified gateway, ACP/A2A backends, memory/knowledge, Web/TUI/Desktop/mobile frontends |

Nexus itself owns cross-engine routing, execution policy, process management,
immutable asset versions, provenance, and cross-engine workflow composition.

## License boundary that cannot be flattened

GenOffice's open/core source is Apache-2.0 and is vendored. Its upstream
`ee/` directory is governed by a separate GenOffice Enterprise License that
does **not** permit public redistribution without an appropriate agreement.
Therefore `engines/genoffice/ee` is deliberately excluded and CI fails if it
appears. This is a legal redistribution boundary, not a hidden technical
dependency.

Open WebUI remains under its own Open WebUI License and its branding is retained
as required by that license. Every vendored engine retains its own LICENSE,
NOTICE, third-party notices, and attribution files.

## Verify the complete in-tree build

```bash
git clone https://github.com/GAN-007/OPEN-SUITES-OFFICE-.git
cd OPEN-SUITES-OFFICE-

python3 scripts/verify_lock.py
python3 scripts/verify_vendored.py --require
python3 scripts/verify_engine_contracts.py
```

The vendored verifier recomputes the file count, byte count, and aggregate
SHA-256 tree fingerprint for every engine and rejects legacy gitlinks.

## Nexus control plane

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
nexus serve
```

Main surfaces:

- `GET /` — build identity and source model.
- `GET /health` — Nexus, adapter, and native-engine state.
- `GET /v1/engines` — all specialist adapters.
- `GET /v1/native/engines` — all in-tree runtimes, capabilities, commands, and process state.
- `POST /v1/native/engines/{engine}/start` — start a registered long-running engine.
- `POST /v1/native/engines/{engine}/stop` — stop it.
- `POST /v1/native/engines/{engine}/install|build|test` — run the native phase against the vendored tree.
- `POST /v1/route` — choose the canonical specialist.
- `POST /v1/execute` — invoke it with approval and provenance enforcement.
- `POST /v1/assets` — immutable content-addressed asset versions.
- `GET /v1/provenance/{id}` — reconstruct execution lineage.

## One CLI

```bash
nexus engine list
nexus engine status graphiti
nexus engine install genoffice
nexus engine build genoffice
nexus engine test genoffice
nexus engine start openmaic
nexus route "compare section 18.4 with appendix C in this 900-page report"
nexus serve
```

CLI-style engines execute from their vendored trees. PageIndex is imported from
its vendored SDK tree. Service engines run their native server/MCP surfaces from
their vendored source and are addressed at non-conflicting Nexus defaults.

## Refreshing an engine without losing provenance

Source upgrades are explicit, not floating:

1. update the exact SHA in `sources.lock.json`;
2. run `python scripts/vendor_sources.py`;
3. review original license/notice changes;
4. run integrity and capability-root verification;
5. run Nexus tests;
6. run the affected engine's native install/build/test gates;
7. run cross-engine acceptance scenarios;
8. commit the resulting source-tree delta.

The vendorizer strips nested Git metadata but preserves source files, modes,
symlinks, nested submodule contents, license files, and notices. It never copies
a path listed in `excluded_paths`.

## Tests

Nexus integration layer:

```bash
python scripts/verify_lock.py
python scripts/verify_vendored.py --require
python scripts/verify_engine_contracts.py
python -m compileall -q nexus_workspace scripts tests
pytest
```

Native engine gates:

```bash
python scripts/engine_tasks.py install --engine genoffice --stop-on-failure
python scripts/engine_tasks.py build --engine genoffice --stop-on-failure
python scripts/engine_tasks.py test --engine genoffice --stop-on-failure
```

The GitHub **Vendored Engine Native Parity** matrix can run these phases for all
ten engines independently.

## Data ownership

| Information / operation | Canonical owner |
|---|---|
| Office document structure/fidelity | GenOffice |
| Classroom/course state | OpenMAIC |
| Enterprise KB/Wiki | WeKnora |
| Temporal facts/history | Graphiti |
| Durable agent/user/project memory | Cognee |
| Stateful browser interaction | Browser Use |
| General AI workspace | Open WebUI |
| Long-document structural retrieval | PageIndex |
| Source-specific internet acquisition | Agent-Reach |
| Realtime voice/task presence | Qwen Audio Agent |
| Cross-engine workflow/audit | Nexus |
| Asset/version identity | Nexus Asset Store |

For implementation boundaries and acceptance gates, see
[`NEXUS_ARCHITECTURE.md`](NEXUS_ARCHITECTURE.md) and
[`docs/RUNTIME.md`](docs/RUNTIME.md).
