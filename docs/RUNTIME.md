# Nexus Runtime

Nexus 0.2 uses an **in-repository engine model**. Runtime code lives under
`engines/`; the application no longer requires Git submodules to obtain its
specialist implementations.

## Clone

```bash
git clone https://github.com/GAN-007/OPEN-SUITES-OFFICE-.git
cd OPEN-SUITES-OFFICE-
python3 scripts/verify_lock.py
python3 scripts/verify_vendored.py --require
python3 scripts/verify_engine_contracts.py
```

The two verification commands check that all ten vendored source trees match
the generated integrity manifest, that no legacy `upstream/*` gitlinks remain,
that restricted GenOffice `ee/` source is not redistributed, and that the
major capability roots for every engine are physically present.

## Control plane

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
nexus serve
```

Nexus listens on port 8787 by default and exposes OpenAPI at `/docs`.

## Native engine management

Nexus owns a runtime catalog for the vendored engines:

```bash
nexus engine list
nexus engine status genoffice
nexus engine install genoffice
nexus engine build genoffice
nexus engine test genoffice
nexus engine adapters
```

For engines with a long-running native service command in
`engines.runtime.json`, Nexus can also manage the process:

```bash
nexus engine start openmaic
nexus engine stop openmaic
```

The same controls are exposed under `/v1/native/engines`.

## Routing and execution

```bash
nexus route 'Compare section 18.4 with appendix C in this long report'
nexus route 'What was the customer limit before the March change?'
nexus route 'Open the vendor portal and submit the approved form'
```

Routing chooses the canonical specialist engine, but the selected implementation
is now inside this repository. CLI engines are executed from their
`engines/<name>` tree, PageIndex is loaded from its vendored SDK, and service
engines use their native HTTP/MCP surfaces while running from their vendored
source.

External side effects remain approval-gated.

## Source refresh

The normal clone already contains engine source. `vendor_sources.py` exists
for controlled upstream refreshes:

```bash
python3 scripts/vendor_sources.py
git add -A
python3 scripts/verify_vendored.py --require
python3 scripts/verify_engine_contracts.py
```

It checks out the exact SHAs in `sources.lock.json`, copies source into
`engines/`, strips nested Git metadata, retains licenses/notices, excludes
paths that cannot legally be redistributed, and generates
`engines/VENDOR_MANIFEST.json`.

## Native parity

```bash
python3 scripts/engine_tasks.py install --engine genoffice --stop-on-failure
python3 scripts/engine_tasks.py build --engine genoffice --stop-on-failure
python3 scripts/engine_tasks.py test --engine genoffice --stop-on-failure
```

The manual **Vendored Engine Native Parity** workflow runs those phases across
all ten engines with their own toolchains.
