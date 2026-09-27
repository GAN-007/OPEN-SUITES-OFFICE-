# Nexus Fusion Architecture

Snapshot: 2026-09-27

## 1. Goal

OPEN SUITES OFFICE — Nexus is a lossless capability federation of ten independently engineered AI systems. It does not replace any upstream implementation with a simplified rewrite. Each complete upstream repository remains a Git submodule pinned to an audited 40-character commit SHA, while Nexus-owned code provides the cross-engine control plane: capability routing, identity boundaries, approvals, asset/version identity, provenance, reproducible source locking, parity gates, and deployment infrastructure.

The governing rule is preservation plus federation:

1. Preserve upstream implementations and native toolchains.
2. Integrate through stable public/native surfaces such as MCP, A2A/ACP, REST, CLI and SDKs.
3. Keep Nexus-owned code outside upstream source trees.
4. Prove upgrades through native upstream tests and cross-engine Nexus tests.
5. Never silently replace specialist semantics with generic adapters.

## 2. Audited source set

| Engine | Pinned revision | Observed tracked files | Canonical Nexus role |
| --- | --- | ---: | --- |
| GenOffice | d9cd4895b99b3e65aa8beea13f95b232329f4c11 | 3,661 | Native Office/PDF/Markdown/HTML fidelity, CLI, MCP |
| OpenMAIC | f2875426ae5712d26f0a76e54e9de763e86027a6 | 3,126 | Multi-agent courses, workbench, classroom, playback, exports |
| WeKnora | 9114e4e4f905be71976a77c684d3f92731e6f9a6 | 4,604 | Enterprise RAG, Agent, Wiki, RBAC, sandbox and MCP |
| Graphiti | 6b4b56ff6f4b1e4e69c3c3c5487cf1b8762c483a | 384 | Temporal context graph and historical facts |
| Cognee | eb90d03740755f5252b8b12cce91fd09970f2d81 | 3,883 | Durable agent/user/project memory |
| Browser Use | 4cbe921673b48a488f5415d9159249afd12a625b | 518 | Stateful browser execution and browser agent tooling |
| Open WebUI | 8bd8b4fac5e059578ac0c74b3c18d11139f88b7d | 5,065 | General self-hosted AI workspace |
| PageIndex | 037a7dbacfb9a19f38b354ce60cee5094b3f854c | 177 | Reasoning-based hierarchical long-document retrieval |
| Agent-Reach | a19a171fa980a0785849596492e0af4db800c82f | 122 | Source-specific internet acquisition and diagnostics |
| Qwen Audio Agent | a73bcbc2e1278bf664df38bdd169ffba1fb2451f | 1,418 | Realtime voice presence and backend task delegation |

Total observed tracked files: 22,958.

The authoritative machine-readable source list is `sources.lock.json`. The `.gitmodules` entries and Git tree gitlinks point to those same revisions.

## 3. Architecture

```text
                                   NEXUS
                                     |
                 +-------------------+-------------------+
                 |                                       |
          EXPERIENCE PLANE                         CONTROL PLANE
                 |                                       |
     +-----------+-----------+             +-------------+-------------+
     |           |           |             |             |             |
 GenOffice    OpenMAIC   Open WebUI     Routing      Approvals     Provenance
     |           |           |             |             |             |
     +-----------+-----------+-------------+-------------+-------------+
                                     |
                               AGENT GATEWAY
                                     |
                       +-------------+-------------+
                       |             |             |
                      MCP           A2A           ACP
                       |             |             |
             +---------+-------------+-------------+---------+
             |                                             |
       CAPABILITY BROKERS                               EVENT/WORKFLOW
             |                                             |
   +---------+----------+----------+----------+             |
   |         |          |          |          |             |
 Office   Classroom  Knowledge   Memory    Browser/Web      |
   |         |          |          |          |             |
 GenOffice OpenMAIC  WeKnora   Graphiti   Browser Use       |
                              Cognee       Agent-Reach      |
                                                           |
                    RETRIEVAL BROKER <---------------------+
                        |
              +---------+---------+
              |         |         |
          PageIndex   WeKnora   Graphiti
                                  |
                                Cognee
```

Nexus is a capability federation, not a flattened fork. MCP is the tool plane. A2A and ACP are agent interoperability planes. Durable workflow state belongs to the Nexus control plane or the owning upstream engine; LangGraph is retained where an upstream uses graph-style reasoning but is not treated as the distributed system database.

## 4. Canonical ownership

Nexus avoids duplicated intelligence by assigning one canonical owner to each information or operation class.

| Information / operation | Canonical owner |
| --- | --- |
| DOCX/XLSX/PPTX and Office-format fidelity | GenOffice |
| PDF native editing/conversion | GenOffice |
| Course/classroom generation and state | OpenMAIC |
| Enterprise knowledge base and Wiki | WeKnora |
| Long-document structural retrieval | PageIndex |
| Time-varying facts and historical validity | Graphiti |
| Durable agent/user/project memory | Cognee |
| Interactive browser state/actions | Browser Use |
| Source-specific web acquisition | Agent-Reach |
| General model/chat workspace | Open WebUI |
| Realtime voice/task presence | Qwen Audio Agent |
| Cross-engine routing/workflow/audit | Nexus |
| Asset identity and immutable versions | Nexus Asset Store |

The same document is not blindly copied to every retrieval and memory system. Nexus stores an original asset once, records immutable versions, and sends references or purpose-specific derived indexes only to engines that need them.

## 5. Protocol boundaries

### MCP

MCP is used for discoverable tool invocation where an upstream exposes MCP. The Nexus MCP HTTP adapter supports JSON-RPC and Streamable HTTP/SSE responses. MCP is not used as the durable event store.

### A2A and ACP

Qwen Audio Agent's current architecture supports a unified client runtime and ACP/A2A backend integration. Nexus therefore treats ACP/A2A as agent-to-agent interoperability protocols rather than its internal database.

### REST/HTTP

WeKnora, Cognee, Open WebUI, OpenMAIC and other services can be connected through native HTTP APIs. The generic JSON adapter preserves method/path/arguments rather than inventing simplified business semantics.

### CLI

GenOffice, Browser Use, Agent-Reach and Qwen-related command surfaces can be invoked using the CLI adapter when their native CLI is the appropriate surface. CLI execution is time bounded and captures exact argv/output for provenance.

### SDK

PageIndex local mode is invoked through its native Python SDK so local vectorless retrieval does not require a cloud MCP dependency.

## 6. Control-plane implementation

The `nexus_workspace` package is executable, not a structural placeholder.

- `models.py`: typed capabilities, engine identities, risk classes and API contracts.
- `routing.py`: deterministic specialist ownership and explicit override support.
- `config.py`: environment-backed endpoints/commands and runtime settings.
- `database.py`: persistent provenance and asset metadata.
- `assets.py`: immutable SHA-256-addressed asset versions.
- `service.py`: execution orchestration, approval enforcement and provenance writes.
- `api.py`: FastAPI control-plane endpoints.
- `cli.py`: runnable Nexus CLI and API server.
- `adapters/*`: HTTP, CLI, MCP and PageIndex SDK transports.

The current API exposes health, engine status, routing, execution, immutable asset creation and provenance retrieval. OpenAPI documentation is produced by FastAPI.

## 7. Side-effect policy

Read-only reasoning and local artifact writes are distinct from externally observable actions. Requests marked `external_side_effect` are rejected unless `approved=true` when approval enforcement is enabled.

Examples include submitting browser forms, sending external messages, purchasing, publishing content, deleting remote resources or other changes outside the local Nexus workspace.

Upstream engines may have stricter approval mechanisms; Nexus never weakens them.

## 8. Asset and provenance model

Every ingested or generated artifact receives:

- stable asset ID,
- immutable version ID,
- monotonically increasing version,
- SHA-256 content digest,
- content length,
- media type,
- persisted byte path,
- actor and timestamp.

Every executed cross-engine action receives:

- execution ID,
- provenance ID,
- actor,
- selected engine and capability,
- action,
- normalized request,
- normalized result,
- timestamp.

This makes work reconstructable without pretending that one engine's internal trace format is identical to another's.

## 9. Retrieval routing

Examples:

- Historical/temporal questions route to Graphiti.
- Long document section/appendix/page reasoning routes to PageIndex.
- Enterprise KB/Wiki queries route to WeKnora.
- Durable memory/previous-session questions route to Cognee.
- Office creation/editing routes to GenOffice.
- Stateful navigation/click/type/form tasks route to Browser Use.
- Platform-specific internet research routes to Agent-Reach.
- Course/classroom tasks route to OpenMAIC.
- Realtime voice tasks route to Qwen Audio Agent.
- General model/chat requests with no specialist signal route to Open WebUI.

Mixed workflows may call several owners sequentially, while each retains authority for its own data semantics.

## 10. Infrastructure

`infra/docker-compose.yml` supplies local development instances of PostgreSQL, Redis, FalkorDB, Qdrant and MinIO. These are infrastructure dependencies, not replacements for the ten applications.

Production deployment must add TLS, managed secrets, network policy, SSO/RBAC, immutable image digests, backups, sandbox isolation, rate controls and observability.

## 11. Reproducibility and source verification

`scripts/verify_lock.py` validates exactly ten unique HTTPS GitHub repositories, safe paths and full SHAs.

`scripts/verify_submodules.py` confirms that initialized submodules are at the exact locked revisions.

`scripts/bootstrap_sources.py` can independently materialize the same pinned trees and refuses dirty checkouts.

`scripts/audit_sources.py` inventories tracked files, extensions, top-level structure, code markers and license/notice files.

The Git submodules are the primary source-preservation mechanism. The bootstrap/audit utilities provide an independent reproducibility and inspection path.

## 12. Native parity gates

`upstream-tests.json` records native install/build/test entry points for all ten engines. The manual `Upstream Parity Gates` GitHub Actions workflow checks out the complete submodule graph, verifies SHAs and can execute install/build/test phases for each engine independently.

Nexus does not replace upstream tests with mocks. Nexus-owned tests cover the integration layer while upstream-native test suites cover upstream behavior.

Required parity areas include:

- GenOffice: Office round-trip fidelity, render checks, CLI and MCP.
- OpenMAIC: generation/workbench, durable sessions, materials, classroom scenes, quizzes/PBL/whiteboard and exports.
- WeKnora: RAG/Agent/Wiki, workspace RBAC/audit, MCP, sandbox/browser/skills and source citations.
- Graphiti: episode ingestion, temporal validity, search, graph drivers and MCP.
- Cognee: remember/recall/improve/forget, session promotion, retrieval routes, permissions and MCP.
- Browser Use: local/cloud browser paths, browser state/actions, extraction, sessions and tool surfaces.
- Open WebUI: models, tools, skills, RAG, channels, authentication and native migrations.
- PageIndex: local tree indexing/retrieval/chat and source locators.
- Agent-Reach: doctor diagnostics, channel health, preferred/fallback routing and credential boundaries.
- Qwen Audio Agent: full-duplex conversation, interruption, background task lifecycle, ACP/A2A adapters and native UIs.

## 13. Cross-engine acceptance scenarios

1. Upload a long PDF; create a PageIndex tree and WeKnora KB representation; promote selected temporal facts to Graphiti and approved durable memory to Cognee; answer with evidence traceable to the source asset.
2. Open a DOCX; obtain external research through Agent-Reach; apply a native GenOffice edit to a new immutable asset version while retaining the original.
3. Ask by voice for a multi-step web task; Qwen delegates through Nexus; Agent-Reach handles optimized read/search; Browser Use performs stateful interaction; approval is required before the committing external action.
4. Build an OpenMAIC course from uploaded files and web materials, personalize from approved Cognee memory, export PPTX, then revise the deck in GenOffice.
5. Ask a question whose factual answer changed over time and verify Graphiti returns historical validity instead of only current state.
6. Delete durable memory and verify Cognee-derived references/tombstones are handled without deleting unrelated WeKnora enterprise KB content.
7. Use Open WebUI alongside Nexus specialist surfaces while preserving identity/resource authorization and Open WebUI's license/branding obligations.

## 14. Security boundaries

- No secrets are committed to source locks, gitmodules or provenance payloads.
- Browser credentials/cookies stay inside their owning runtime boundary.
- MCP endpoints should be allowlisted and identity bound in production.
- URL-fetching services require SSRF controls.
- File execution and active document content must be sandboxed/quarantined according to policy.
- External side effects require explicit approval.
- Tenant IDs must scope graph, vector, object and relational data.
- Native upstream security controls remain authoritative and are never bypassed by Nexus.

## 15. Licensing boundaries

The root Apache-2.0 license applies only to Nexus-owned integration code. Every submodule remains governed by its upstream license, notices, trademarks and third-party terms.

In particular, the pinned Open WebUI code uses its current Open WebUI License with branding-preservation requirements, and GenOffice contains an `ee/` area under separate enterprise terms. Nexus keeps these boundaries visible rather than relicensing or silently rebadging upstream code.

## 16. Upgrade procedure

A source upgrade is controlled:

1. Change one candidate upstream SHA.
2. Verify/re-audit the source.
3. Run the engine's native install/build/test gate.
4. Run Nexus adapter contract tests.
5. Run affected cross-engine scenarios.
6. Review schema/data migration changes.
7. Review license/notice delta.
8. Promote the lock and submodule gitlink only after required gates pass.

No automated job may silently move pinned upstream revisions in production.

## 17. Definition of done

Nexus is considered lossless only when all ten exact source trees are materializable, required native parity gates pass, specialist capabilities remain available, cross-engine scenarios pass, external side effects are policy checked, artifacts remain versioned and traceable, retrieval provides evidence, durable workflow state survives restart where applicable, upgrade changes are reproducible, and license/trademark boundaries remain intact.

Anything less is an integration subset rather than the full lossless federation.
