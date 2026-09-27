# OPEN SUITES OFFICE — Nexus

**More useful every day. Not another list of chatbots.**

OPEN SUITES OFFICE — Nexus is an in-repository AI workspace built from the real source of ten specialist engines and a Nexus-owned control plane. The redistributable source code is committed under `engines/*`; pinned `upstream/*` Git submodules remain as reproducible source mirrors used to audit and refresh those snapshots.

This means Nexus is **not merely a set of links to external projects**. The application repository contains the actual permitted engine source trees and its runtime defaults to them.

## In-house engines

| Engine | In-repository role | Native capabilities retained |
|---|---|---|
| GenOffice | Native Office/PDF/Markdown/HTML engine | Docs, Sheets, Slides, PDF, Markdown, HTML, CLI, MCP, agent core, native engines |
| OpenMAIC | Multi-agent interactive classroom | Workbench, durable sessions, generation, classroom, quizzes, PBL, whiteboard, exports, skills |
| WeKnora | Enterprise knowledge and agent runtime | RAG, Agent, Wiki, RBAC, MCP, sandboxes, browser skill, connectors, memory |
| Graphiti | Temporal context graph | Temporal facts, episodes, graph search, graph drivers, MCP |
| Cognee | Durable memory layer | remember/recall/improve/forget, graph/vector/code memory, APIs and MCP |
| Browser Use | Stateful browser automation | Browser agent, actions, sessions, auth state, extraction, screenshots, MCP/CLI |
| Open WebUI | General self-hosted AI workspace | Web UI, backend, RAG, tools, skills, models, memory, automations, voice and integrations |
| PageIndex | Long-document reasoning | Local vectorless indexing, tree retrieval and document chat |
| Agent-Reach | Source-specific internet access | CLI, channel backends, diagnostics, search/read integrations |
| Qwen Audio Agent | Realtime voice/task runtime | Full-duplex voice, web/TUI/desktop/mobile surfaces, memory/knowledge, ACP/A2A backends |

The exact source SHAs, permitted vendor paths and license restrictions are declared in `sources.lock.json`. `vendor.manifest.json` records a deterministic SHA-256 tree digest and file count for every committed engine snapshot.

## Source layout

```text
OPEN-SUITES-OFFICE-
├── engines/                 # runtime-preferred, committed engine source
│   ├── genoffice/
│   ├── openmaic/
│   ├── weknora/
│   ├── graphiti/
│   ├── cognee/
│   ├── browser-use/
│   ├── open-webui/
│   ├── pageindex/
│   ├── agent-reach/
│   └── qwen-audio-agent/
├── upstream/                # pinned Git source mirrors for refresh/audit
├── nexus_workspace/         # Nexus routing, policy, assets, provenance, API
├── scripts/                 # source sync, verification, parity and audit tooling
├── policies/
├── schemas/
├── infra/
└── tests/
```

## Reproduce or refresh the in-house source

A normal clone already contains the vendored engines:

```bash
git clone https://github.com/GAN-007/OPEN-SUITES-OFFICE-.git
cd OPEN-SUITES-OFFICE-
python3 scripts/verify_lock.py
python3 scripts/verify_vendored.py
```

To prove that the committed copies are identical to the permitted portions of the pinned upstream revisions:

```bash
git submodule update --init --recursive
python3 scripts/verify_submodules.py
python3 scripts/verify_vendored.py --compare-sources
```

To regenerate all vendored snapshots from the locked revisions:

```bash
python3 scripts/vendor_upstreams.py
python3 scripts/verify_vendored.py --compare-sources
```

## What Nexus adds on top of the engine code

Nexus intertwines the ten codebases without flattening away their specialist behavior:

- **Capability routing** sends Office work to GenOffice, temporal facts to Graphiti, durable memory to Cognee, enterprise KB work to WeKnora, long-document structural queries to PageIndex, stateful browser actions to Browser Use, source-specific research to Agent-Reach, general model work to Open WebUI, classrooms to OpenMAIC and realtime voice work to Qwen Audio Agent.
- **Vendored-source resolution** makes `engines/*` the default runtime source. `upstream/*` can be selected only for audit/debug use.
- **Immutable asset versioning** stores content-addressed file versions instead of destructive overwrites.
- **Cross-engine provenance** records actor, engine, capability, action, request, output and execution IDs.
- **Side-effect approvals** fail closed for externally observable actions unless explicitly approved.
- **Polyglot preservation** retains each engine's real TypeScript/Node, Go, Python, native/Rust, browser and database implementation rather than translating it into simplified wrappers.
- **Native parity gates** execute each engine's own install/build/test commands from the vendored tree.

## Control-plane API

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
nexus serve
```

Key endpoints:

- `GET /health` — control-plane, source and adapter status.
- `GET /v1/sources` — confirms whether each engine is running from the committed vendor tree.
- `GET /v1/engines` — native transport configuration.
- `POST /v1/route` — deterministic capability routing.
- `POST /v1/execute` — execute through the selected engine with approval enforcement and provenance.
- `POST /v1/assets` — immutable content-addressed asset versions.
- `GET /v1/provenance/{id}` — execution audit trail.

## Native builds and tests

```bash
pip install -e '.[dev]'
python scripts/verify_lock.py
python scripts/verify_vendored.py
python -m compileall -q nexus_workspace scripts tests
pytest
```

Native engine commands in `upstream-tests.json` now point to the committed `engines/*` source trees. The **Native Vendored Engine Parity Gates** workflow can install, build and test each engine with its own native toolchain.

## Infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d
```

The shared development data plane supplies PostgreSQL, Redis, FalkorDB, Qdrant and MinIO. Each native engine still retains its own required services, models, browser binaries, provider keys and deployment requirements.

## License boundary that cannot be removed

All redistributable engine source is vendored. One directory is intentionally excluded: `engines/genoffice/ee/`.

The pinned GenOffice Enterprise License says its `ee/` source may be copied/modified for development and testing, but redistribution or production use requires a valid enterprise agreement with Mainfunc, Inc. Because this repository is public, Nexus must not commit that source without such permission.

For a locally licensed/development environment:

```bash
git submodule update --init upstream/genoffice
python scripts/install_restricted.py --engine genoffice --acknowledge-license
```

That overlay is git-ignored. This is the only deliberate source exclusion in the vendor process. Open WebUI is vendored with its copyright, license and branding requirements intact.

See `NEXUS_ARCHITECTURE.md`, `LICENSED_COMPONENTS.md` and `docs/RUNTIME.md` for the detailed model.
