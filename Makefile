PYTHON ?= python3

.PHONY: verify-lock verify-submodules bootstrap audit test lint serve infra-up infra-down upstream-test

verify-lock:
	$(PYTHON) scripts/verify_lock.py

verify-submodules: verify-lock
	$(PYTHON) scripts/verify_submodules.py

bootstrap: verify-lock
	git submodule sync --recursive
	git submodule update --init --recursive
	$(PYTHON) scripts/verify_submodules.py

audit: verify-submodules
	$(PYTHON) scripts/audit_sources.py

test: verify-lock
	pytest

lint:
	ruff check nexus_workspace tests scripts

serve:
	nexus serve

infra-up:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down

upstream-test:
	$(PYTHON) scripts/engine_tasks.py test
