# Nexus Runtime

## Runtime source policy

Nexus defaults to `NEXUS_ENGINE_SOURCE_MODE=vendored`. Every adapter that executes code locally resolves its engine from `engines/<engine>` first and fails closed if that committed source tree is absent. `upstream/*` is an audit/refresh mirror, not the normal runtime.

Verify a normal clone:

```bash
python3 scripts/verify_lock.py
python3 scripts/verify_vendored.py
nexus source-status
```

## Rebuild the vendored engine trees from origin

```bash
git submodule update --init --recursive
python3 scripts/verify_submodules.py
python3 scripts/vendor_upstreams.py
python3 scripts/verify_vendored.py --compare-sources
```

The verification compares deterministic file counts and SHA-256 tree digests after excluding only paths explicitly marked as non-redistributable in `sources.lock.json`.

## GenOffice enterprise overlay

`engines/genoffice/ee/` is deliberately absent from the public repository because its upstream enterprise license forbids redistribution without an enterprise agreement. For development/testing or an appropriately licensed production environment:

```bash
git submodule update --init upstream/genoffice
python3 scripts/install_restricted.py --engine genoffice --acknowledge-license
```

The overlay is git-ignored.

## Run the control plane

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
nexus serve
```

The API listens on `http://127.0.0.1:8787` when configured that way and exposes Swagger/OpenAPI at `/docs`.

## Engine execution

`POST /v1/execute` invokes the selected native adapter. Local CLI/SDK adapters execute with their working directory inside the vendored source tree. Server-oriented engines retain their native runtimes and can be launched from their own vendored directories; Nexus connects to them over their native HTTP/MCP/agent protocol surfaces.

Externally observable side effects remain approval-gated. Native upstream approval/security controls remain authoritative and can be stricter.

## Native parity

`upstream-tests.json` points at `engines/*`, not `upstream/*`. The manual **Native Vendored Engine Parity Gates** workflow initializes the locked source mirrors, proves source-to-vendor equality, then runs each engine's own install/build/test commands against the committed vendored copy.

## Development infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d
```

This supplies shared PostgreSQL, Redis, FalkorDB, Qdrant and MinIO services. Individual engines may require additional services, browser binaries, model weights or provider credentials defined by their retained native source.
