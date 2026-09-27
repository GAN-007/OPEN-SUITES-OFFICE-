# Nexus Runtime

## Clone the complete source federation

```bash
git clone --recurse-submodules https://github.com/GAN-007/OPEN-SUITES-OFFICE-.git
cd OPEN-SUITES-OFFICE-
python3 scripts/verify_lock.py
python3 scripts/verify_submodules.py
```

Every `upstream/*` directory is a real Git submodule pinned to the SHA in `sources.lock.json`. This preserves the complete source, history boundary, native test suite and license boundary of each specialist engine.

## Start infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d
```

## Run the control plane

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
nexus serve
```

The API listens on `http://127.0.0.1:8787` by default. Swagger/OpenAPI is available at `/docs`.

## Routing

```bash
nexus route 'Compare section 18.4 with appendix C in this long report'
nexus route 'What did this customer believe before the March policy change?'
nexus route 'Open the vendor portal and submit the approved form'
```

The router selects the canonical engine owner, while callers can explicitly override the engine or capability when required.

## Engine execution

`POST /v1/execute` invokes the configured adapter. External-side-effect actions are rejected unless the caller explicitly marks the request approved. Native upstream UIs and CLIs remain directly usable; Nexus does not hide or replace any upstream surface.

## Asset/version model

`POST /v1/assets` stores immutable content-addressed versions. Further versions never overwrite prior bytes. Specialist indexes should reference the Nexus asset/version ID so source provenance remains reconstructable.
