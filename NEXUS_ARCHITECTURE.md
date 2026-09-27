# Nexus In-Repository Architecture

Snapshot: 2026-09-27  
Architecture generation: 0.2

## 1. Objective

Nexus is a single repository and control plane containing the redistributable
implementation source of ten specialist AI engines. The product does not reduce
those engines to wrappers. Their native source trees remain intact under
`engines/`; Nexus adds a common execution and governance plane above them.

The design has four invariants:

1. **Source is local** — specialist runtime source is committed in this repo.
2. **Native semantics survive** — native CLIs, APIs, MCP, ACP/A2A, SDKs, UIs,
   migrations, models, and tests remain available.
3. **Canonical ownership prevents duplication** — Nexus composes engines but
   does not pretend their storage semantics are interchangeable.
4. **Every imported byte is attributable** — immutable source SHAs, original
   licenses/notices, and per-tree integrity fingerprints are retained.

## 2. Source layout

```text
OPEN-SUITES-OFFICE-
├── nexus_workspace/         # Nexus-owned control plane
├── engines/
│   ├── genoffice/           # vendored open/core source
│   ├── openmaic/
│   ├── weknora/
│   ├── graphiti/
│   ├── cognee/
│   ├── browser-use/
│   ├── open-webui/
│   ├── pageindex/
│   ├── agent-reach/
│   ├── qwen-audio-agent/
│   └── VENDOR_MANIFEST.json
├── config/
├── policies/
├── schemas/
├── infra/
├── scripts/
├── tests/
├── sources.lock.json
└── engines.runtime.json
```

The former `upstream/*` gitlinks and `.gitmodules` are removed by the
vendorization transition and CI rejects their reintroduction.

## 3. Product topology

```text
                              NEXUS
                                |
                +---------------+---------------+
                |                               |
          EXPERIENCE PLANE                CONTROL PLANE
                |                               |
       +--------+--------+             +--------+--------+
       |        |        |             |        |        |
   GenOffice OpenMAIC Open WebUI    Router   Policy  Provenance
       |        |        |             |        |        |
       +--------+--------+-------------+--------+--------+
                                |
                         RUNTIME CATALOG
                                |
           +--------------------+--------------------+
           |                    |                    |
          CLI/API              MCP               ACP/A2A
           |                    |                    |
  +--------+-------+       +----+-----+        +-----+------+
  |        |       |       |          |        |            |
Office  Browser  Reach   Graphiti  WeKnora   Qwen Audio  Agents
  |        |       |       |          |        |
  +--------+-------+-------+----------+--------+
                   |
            RETRIEVAL / MEMORY
        +----------+----------+----------+
        |          |          |          |
    PageIndex   WeKnora    Graphiti    Cognee
```

## 4. Runtime catalog

`engines.runtime.json` is the machine-readable bridge from the Nexus control
plane to the native implementation trees. For every engine it defines:

- vendored source root;
- runtime kind;
- native install commands;
- native build commands;
- native test commands;
- native long-running start command where applicable;
- native CLI command where applicable;
- non-conflicting Nexus environment overrides;
- capability inventory.

`RuntimeCatalog` resolves those entries; `NativeProcessManager` runs lifecycle
and parity phases from the actual engine directory and records PID/log state.

Default local service ports are deliberately separated:

| Service | Nexus local port |
|---|---:|
| OpenMAIC | 3001 |
| WeKnora | 8080 |
| Graphiti MCP | 8002 |
| Cognee API | 8003 |
| Open WebUI | 8084 |
| Nexus control plane | 8787 |

Qwen Audio normally owns its own local gateway/runtime. CLI engines do not need a
persistent port.

## 5. Native integration surfaces

### GenOffice

Nexus invokes the vendored GenOffice CLI from
`engines/genoffice/packages/cli/bin/genoffice`. The same source tree retains
Docs, Sheets, Slides, PDF, Markdown, HTML applications, document engines,
render/conversion pipelines, agent-core, skills and MCP support.

### OpenMAIC

The complete Next.js/TypeScript workspace remains present. Nexus can run the
native service and route classroom/course work to it without replacing its
generation, orchestration, workbench, playback, quiz, PBL, whiteboard, material,
export, or skill implementation.

### WeKnora

The Go backend, frontend, document reader, CLI, migrations, MCP server, sandbox
and enterprise knowledge logic remain in-tree. Nexus addresses its native API
rather than reimplementing WeKnora's knowledge-base semantics.

### Graphiti

The Python core and MCP server are in-tree. Nexus uses the MCP plane for
temporal episode/entity/fact operations while Graphiti remains authoritative for
temporal validity and graph semantics.

### Cognee

Cognee's Python memory engine, API, MCP, frontend and evaluation code remain
in-tree. Durable remember/recall/improve/forget semantics stay owned by Cognee.

### Browser Use

Browser agent/runtime code, tools, MCP, profiles, extraction and test suites are
in-tree. Nexus invokes the native CLI/runtime from that source.

### Open WebUI

Frontend and backend code are in-tree under the Open WebUI License. Its branding
is preserved. Nexus can use it as the general AI workspace while retaining its
models, agents, RAG, tools, skills, memory, channels, scheduling, media and RBAC
surfaces.

### PageIndex

Nexus imports the local vendored SDK path directly, keeping vectorless tree
indexing and reasoning retrieval local to the repository.

### Agent-Reach

The complete channel/router/diagnostic implementation is vendored and its native
CLI is invoked from the in-tree source.

### Qwen Audio Agent

Gateway, server, CLI, web, TUI, desktop, mobile, ACP/A2A adapters, memory and
knowledge code are in-tree. Nexus invokes the vendored CLI/gateway.

## 6. Routing versus implementation

Routing is not the implementation. It merely selects which **local implementation**
owns a request. For example:

- a DOCX edit routes to the GenOffice code physically under `engines/genoffice`;
- a historical fact query routes to the local Graphiti MCP runtime;
- a memory recall routes to the local Cognee API/runtime;
- a browser form task routes to local Browser Use code;
- a 900-page structural query executes through the vendored PageIndex SDK;
- source-specific web acquisition executes through vendored Agent-Reach;
- a voice task executes through vendored Qwen Audio Agent.

This is the key architectural change from the prior submodule federation.

## 7. Source integrity

`scripts/vendor_sources.py` materializes each audited source SHA into
`engines/`, including nested submodule content. It strips only Git metadata and
explicitly excluded paths.

`engines/VENDOR_MANIFEST.json` records for every engine:

- source repository;
- source commit;
- vendored path;
- exclusions/restrictions;
- file count;
- total byte count;
- aggregate SHA-256;
- largest source files.

`scripts/verify_vendored.py` recomputes that state in CI.

`scripts/verify_engine_contracts.py` separately proves that the major
capability-bearing directories are present. This catches a tree that might be
internally consistent but accidentally incomplete.

## 8. Licensing boundary

All ten engines retain their upstream terms.

GenOffice core can be vendored under Apache-2.0. GenOffice `ee/` cannot be
publicly redistributed under its current enterprise license without an
appropriate agreement, so it is excluded and treated as an optional licensed
extension boundary.

Open WebUI remains branded and governed by the Open WebUI License.

No root Nexus license overrides an engine's own license.

## 9. Native parity

Nexus-owned tests prove the integration plane. Native engine tests prove the
specialist engines.

The parity matrix runs each engine's own install/build/test commands from
`engines/<name>`. The goal is not “a wrapper can reach a URL”; it is “the
native source present in this repository still builds and its own tests still
pass.”

## 10. Cross-engine acceptance scenarios

A release candidate is expected to prove at least these compositions:

1. **Document → retrieval → knowledge → memory**: store a PDF asset, index with
   PageIndex, register enterprise knowledge in WeKnora, promote time-sensitive
   facts to Graphiti and durable conclusions to Cognee, then answer with
   provenance.
2. **Research → Office edit**: acquire source material through Agent-Reach,
   perform stateful browser work where required with Browser Use, and create a
   new GenOffice document version without destroying the original.
3. **Voice → delegated task**: Qwen Audio maintains the live conversation while
   Nexus delegates specialist work and returns the result to the same task
   context.
4. **Topic → classroom → PPTX → Office revision**: OpenMAIC builds the classroom
   and export; GenOffice performs native deck revision.
5. **Temporal recall**: Graphiti distinguishes what was true before and after a
   fact change.
6. **Memory lifecycle**: Cognee forget operations do not destroy unrelated
   WeKnora enterprise knowledge.
7. **General workspace**: Open WebUI remains usable as the broad model/tool
   surface while specialists remain available through Nexus.

## 11. Definition of complete

For the public repository, “complete in-house” means:

- all redistributable source of the ten pinned engines is physically tracked
  under `engines/`;
- no runtime submodule fetch is required;
- excluded/restricted code is explicitly identified rather than silently
  copied;
- each engine's principal capability roots exist;
- Nexus can enumerate and address all ten local runtimes;
- native install/build/test commands are retained;
- Nexus integration tests pass;
- source-tree integrity passes;
- licenses/notices remain attached to their original code;
- cross-engine actions remain policy- and provenance-aware.

That is a monorepo implementation, not a list of remote integrations.
