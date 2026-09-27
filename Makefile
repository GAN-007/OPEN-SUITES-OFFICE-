PYTHON ?= python3

.PHONY: verify-lock verify-submodules verify-vendored bootstrap refresh-vendor audit test lint serve infra-up infra-down upstream-test

verify-lock:
	$(PYTHON) scripts/verify_lock.py

verify-submodules: verify-lock
	$(PYTHON) scripts/verify_submodules.py

verify-vendored: verify-lock
	$(PYTHON) scripts/verify_vendored.py

bootstrap: verify-lock verify-vendored

refresh-vendor: verify-lock
	git submodule sync --recursive
	git submodule update --init --recursive
	$(PYTHON) scripts/verify_submodules.py
	$(PYTHON) scripts/vendor_upstreams.py
	$(PYTHON) scripts/verify_vendored.py --compare-sources

audit: verify-submodules
	$(PYTHON) scripts/audit_sources.py

test: verify-vendored
	pytest

lint:
	ruff check nexus_workspace tests scripts

serve: verify-vendored
	nexus serve

infra-up:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down

upstream-test: verify-vendored
	$(PYTHON) scripts/engine_tasks.py test
