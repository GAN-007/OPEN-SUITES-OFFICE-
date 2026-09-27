PYTHON ?= python3

.PHONY: verify-lock verify-vendored bootstrap vendor audit test lint serve infra-up infra-down engine-test engine-build engine-install

verify-lock:
	$(PYTHON) scripts/verify_lock.py

verify-vendored: verify-lock
	$(PYTHON) scripts/verify_vendored.py --require
	$(PYTHON) scripts/verify_engine_contracts.py

vendor: verify-lock
	$(PYTHON) scripts/vendor_sources.py
	git add -A
	$(PYTHON) scripts/verify_vendored.py --require
	$(PYTHON) scripts/verify_engine_contracts.py

bootstrap: vendor

audit: verify-vendored
	$(PYTHON) scripts/audit_sources.py

test: verify-lock
	$(PYTHON) -m compileall -q nexus_workspace scripts tests
	pytest

lint:
	ruff check nexus_workspace tests scripts

serve:
	nexus serve

infra-up:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down

engine-install:
	$(PYTHON) scripts/engine_tasks.py install

engine-build:
	$(PYTHON) scripts/engine_tasks.py build

engine-test:
	$(PYTHON) scripts/engine_tasks.py test
