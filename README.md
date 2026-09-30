# OPEN SUITES OFFICE — Nexus

**More useful every day. Not another list of chatbots.**

OPEN SUITES OFFICE — Nexus is a lossless AI-workspace federation that preserves and unifies ten specialist AI systems instead of reimplementing reduced copies of them. The complete upstream repositories are pinned as Git submodules, while Nexus-owned code provides routing, approvals, immutable assets, provenance, orchestration boundaries, deployment infrastructure and a single control-plane API.

## Complete upstream engines

| Engine | Pinned role in Nexus | Native surfaces preserved |
|---|---|---|
| GenOffice | Native Office/PDF/Markdown/HTML editing | Electron apps, engines, CLI, MCP, skills |
| OpenMAIC | Multi-agent interactive classroom | Workbench, classroom, quizzes, PBL, whiteboard, exports, skills |
| WeKnora | Enterprise knowledge and agent workflows | RAG, Agent, Wiki, RBAC, MCP, sandboxes, connectors |
| Graphiti | Temporal context graph | Python library, MCP, graph drivers, temporal search |
| Cognee | Durable agent memory | remember/recall/improve/forget, graph/vector/code memory, MCP/API |
| Browser Use | Stateful browser automation | Agent, browser runtime, tools, MCP, cloud/local integrations |
| Open WebUI | General self-hosted AI workspace | Svelte UI, FastAPI backend, RAG, tools, skills, models |
| PageIndex | Reasoning-based long-document retrieval | Local SDK, Flash indexer, agent integrations |
| Agent-Reach | Source-specific internet acquisition | CLI, channel backends, diagnostics, skills |
| Qwen Audio Agent | Realtime voice/task presence | Web/TUI/Desktop/mobile, unified runtime, ACP/A2A backends |

The exact upstream SHAs are in [`sources.lock.json`](sources.lock.json). The submodule gitlinks point to those same SHAs, so a recursive clone materializes the complete audited source trees rather than partial ports or generated approximations.

## Clone everything

```bash
git clone --recurse-submodules https://github.com/GAN-007/OPEN-SUITES-OFFICE-.git
cd OPEN-SUITES-OFFICE-
python3 scripts/verify_lock.py
python3 scripts/verify_submodules.py
```

If the repository was cloned without submodules:

```bash
make bootstrap
```

## What Nexus adds

Nexus does not replace specialist engines. It adds the missing cross-product layer:

- **Capability routing** sends Office work to GenOffice, temporal facts to Graphiti, durable memory to Cognee, enterprise KB questions to WeKnora, long-document structural queries to PageIndex, web actions to Browser Use, source-specific research to Agent-Reach, general model work to Open WebUI, classrooms to OpenMAIC and realtime voice to Qwen Audio Agent.
- **Immutable asset versioning** stores original bytes once and creates content-addressed versions rather than destructive overwrites.
- **Cross-engine provenance** records actor, engine, capability, action, request, output and execution IDs for reconstructable work.
- **Side-effect approvals** prevent externally observable actions from being executed through the Nexus control plane unless the caller explicitly approves them.
- **Polyglot preservation** keeps native TypeScript/Node, Go, Python, Rust/native components, browser runtimes and databases intact.
- **Reproducible parity gates** run each upstream project's own build/test command at its locked revision instead of substituting Nexus mocks for upstream behavior.

## Control-plane API

Create a local environment and run the API:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
nexus serve
```

The service exposes:

- `GET /health` — Nexus and adapter configuration status.
- `GET /v1/engines` — all ten engine transports.
- `GET /v1/systemone/health` — shared GAN Decision Plane provider readiness without exposing secrets.
- `POST /v1/systemone` — Jev-compatible typed decision gateway with configurable Laya/Jev primary/fallback providers.
- `POST /v1/route` — deterministic capability ownership routing.
- `POST /v1/execute` — execute through the selected adapter with approval enforcement and provenance.
- `POST /v1/assets` — create immutable content-addressed asset versions.
- `GET /v1/provenance/{id}` — retrieve the audit chain for an execution.

Interactive OpenAPI documentation is served at `/docs`.

## Shared GAN Decision Plane

Nexus now also hosts the common System-One gateway used by the wider GAN project
ecosystem. Calling applications keep their own domain-specific questions and
policy boundaries, but can point their existing System-One base URL at Nexus
instead of coupling directly to one model vendor.

The gateway preserves the incoming `state + questions` contract and forwards it
to a configured provider at `/v1/systemone`. It currently supports Laya and
Jev-compatible HTTP providers, with optional ordered failover. Provider failures
produce a gateway error; calling applications retain their existing fail-open or
human-review behavior.

Example local configuration:

```bash
NEXUS_DECISION_PLANE_PRIMARY_PROVIDER=laya
NEXUS_DECISION_PLANE_FALLBACK_PROVIDER=
NEXUS_LAYA_BASE_URL=http://127.0.0.1:8000
NEXUS_LAYA_API_KEY=
```

A calling project can then use:

```bash
<PROJECT>_SYSTEM_ONE_BASE_URL=http://nexus-host:8787
```

The gateway never authorizes project actions. GALIKA submission gates, HMS
clinical supervision, HR permissions, SEVI finance/credit controls, telephony
tool authority, trading risk controls and every other domain-specific policy
remain authoritative in their respective applications.

## Infrastructure

A local development data plane is provided for the shared services Nexus and several upstream engines commonly require:

```bash
docker compose -f infra/docker-compose.yml up -d
```

This launches PostgreSQL, Redis, FalkorDB, Qdrant and MinIO with persistent local volumes. Production deployments must replace the development credentials and apply TLS, secret management, network isolation, SSO/RBAC, immutable image digests and sandbox policies.

## Tests

Nexus-owned integration code:

```bash
pip install -e '.[dev]'
python scripts/verify_lock.py
ruff check nexus_workspace tests scripts
pytest
```

Native upstream parity gates are deliberately separate because they preserve each project's real toolchain:

```bash
python scripts/engine_tasks.py install --engine genoffice --stop-on-failure
python scripts/engine_tasks.py build --engine genoffice --stop-on-failure
python scripts/engine_tasks.py test --engine genoffice --stop-on-failure
```

The manual `Upstream Parity Gates` GitHub Actions workflow can run the same install/build/test sequence independently for all ten engines.

## Source-of-truth rules

| Information / operation | Canonical owner |
|---|---|
| Office document structure and fidelity | GenOffice |
| Classroom/course state | OpenMAIC |
| Enterprise knowledge base / Wiki | WeKnora |
| Time-varying facts | Graphiti |
| Durable agent/user/project memory | Cognee |
| Stateful browser interaction | Browser Use |
| General model/chat workspace | Open WebUI |
| Long-document structural retrieval | PageIndex |
| Source-specific internet acquisition | Agent-Reach |
| Realtime voice interaction | Qwen Audio Agent |
| Cross-engine workflow/audit state | Nexus |
| File/version metadata | Nexus Asset Store |

This avoids copying every document into every retrieval system. The original asset is stored once; engines receive the reference or derivative index they actually need.

## License boundaries

The Apache-2.0 `LICENSE` at the root covers only Nexus-owned integration code. The ten submodules remain governed by their own upstream terms. Current Open WebUI source includes branding-preservation requirements, and GenOffice's `ee/` directory has a separate enterprise license. Nexus intentionally keeps these source and license boundaries visible.

For the detailed architecture, failure domains, data flows and parity definition, see [`NEXUS_ARCHITECTURE.md`](NEXUS_ARCHITECTURE.md) and [`docs/RUNTIME.md`](docs/RUNTIME.md).
