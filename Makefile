# OctoLLM developer entry points.
#
# `README.md` has told people to run `make lint`, `make test` and `make help` since
# Phase 0. There was no Makefile. This is that file, and the rule governing it is:
#
#   EVERY TARGET HERE RUNS TODAY, AND CI INVOKES THESE TARGETS RATHER THAN ITS OWN
#   COPY OF THE COMMANDS.
#
# Both halves matter. A target that does not work is worse than a missing one -- it
# is the same failure this repository already had at scale, where documentation
# described a system that was never built. And a CI job that inlines its commands
# drifts from the local ones silently, so "green on my machine" and "green in CI"
# stop meaning the same thing. If you add a check, add it here first and have the
# workflow call it.
#
# Targets for things that do not work yet (`up`, `smoke`, `eval`, `release-gate`)
# are deliberately ABSENT rather than stubbed. They arrive with the stages that make
# them true: compose in Stage 3, the eval harness in Stage 10, the release pipeline
# in Stage 12.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

VERSION := $(shell cat VERSION)
PYTHON ?= python3

ORCHESTRATOR := services/orchestrator
SDK_PY       := sdks/python/octollm-sdk
SDK_TS       := sdks/typescript/octollm-sdk

# Collection floors. A suite that silently collects zero tests reports exactly what a
# suite that ran them all reports; these are what separate the two. Raise one when you
# add tests. Never lower one to make a red build green -- that is the bug, not the fix.
FLOOR_ORCHESTRATOR := 150
FLOOR_SDK_PY       := 28
FLOOR_SDK_TS_FILES := 3
FLOOR_RUST_IGNORED := 17

.PHONY: help
help: ## Show this help
	@printf '\033[1mOctoLLM %s\033[0m\n\n' '$(VERSION)'
	@grep -hE '^[a-zA-Z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@printf '\n  %s\n' 'CI runs exactly these targets -- see .github/workflows/ci.yml'

# =============================================================================
# Install
# =============================================================================

.PHONY: install
install: ## Install both Python packages (editable) and the TypeScript SDK
	$(PYTHON) -m pip install -e "$(ORCHESTRATOR)[dev]"
	$(PYTHON) -m pip install -e "$(SDK_PY)[dev]"
	cd $(SDK_TS) && npm ci

# =============================================================================
# Lint and format
# =============================================================================

.PHONY: lint
lint: lint-python lint-rust lint-typescript lint-config ## Run every linter

.PHONY: lint-python
lint-python: ## ruff + black (check only)
	ruff check . --output-format=$${RUFF_FORMAT:-full}
	black --check --diff .

.PHONY: lint-rust
lint-rust: ## cargo fmt + clippy across the whole workspace
	cargo fmt --all -- --check
	cargo clippy --workspace --all-targets --all-features -- -D warnings

.PHONY: lint-typescript
lint-typescript: ## eslint + tsc for the TypeScript SDK
	cd $(SDK_TS) && npm run lint && npm run build

.PHONY: lint-config
lint-config: ## yamllint, OpenAPI validity, shellcheck, actionlint
	yamllint -c .yamllint.yaml .github/ infrastructure/ codecov.yml
	openapi-spec-validator docs/api/openapi/*.yaml
	@mapfile -t scripts < <(git ls-files '*.sh'); \
	  printf 'shellcheck: %d scripts\n' "$${#scripts[@]}"; \
	  test "$${#scripts[@]}" -gt 0; \
	  shellcheck "$${scripts[@]}"
	actionlint

.PHONY: format
format: ## Rewrite Python and Rust in place (the only targets that MODIFY files)
	ruff check . --fix
	black .
	cargo fmt --all
	cd $(SDK_TS) && npm run format

.PHONY: typecheck
typecheck: ## mypy over the orchestrator and the Python SDK
	mypy $(ORCHESTRATOR)/app $(SDK_PY)/octollm_sdk

# =============================================================================
# Test
# =============================================================================

.PHONY: test
test: test-rust test-orchestrator test-sdk-python test-sdk-typescript ## Run every suite

.PHONY: test-rust
test-rust: ## Rust workspace tests (Redis-backed ones need `make redis`)
	cargo test --workspace --all-features

.PHONY: test-rust-redis
test-rust-redis: ## The Redis-backed Rust tests; needs Redis on localhost:6379
	@output=$$(cargo test --workspace --all-features -- --ignored 2>&1); \
	  echo "$$output"; \
	  ran=$$(echo "$$output" | grep -oE '^test result: ok\. [0-9]+ passed' \
	         | grep -oE '[0-9]+' | awk '{s+=$$1} END {print s+0}'); \
	  echo "Redis-backed tests that ran: $$ran (floor $(FLOOR_RUST_IGNORED))"; \
	  if [ "$$ran" -lt $(FLOOR_RUST_IGNORED) ]; then \
	    echo "::error::expected at least $(FLOOR_RUST_IGNORED) Redis-backed tests, $$ran ran"; \
	    exit 1; \
	  fi

.PHONY: test-orchestrator
test-orchestrator: ## Orchestrator suite, coverage enforced at 85% by its pytest config
	@cd $(ORCHESTRATOR) && collected=$$($(PYTHON) -m pytest tests/ --collect-only -q \
	    -p no:cacheprovider --no-cov 2>&1 \
	    | grep -oE '[0-9]+ tests? collected' | grep -oE '^[0-9]+' | tail -1); \
	  echo "collected=$${collected:-0} (floor $(FLOOR_ORCHESTRATOR))"; \
	  if [ "$${collected:-0}" -lt $(FLOOR_ORCHESTRATOR) ]; then \
	    echo "::error::orchestrator collected $${collected:-0} tests, floor is $(FLOOR_ORCHESTRATOR)"; \
	    exit 1; \
	  fi
	cd $(ORCHESTRATOR) && $(PYTHON) -m pytest tests/

.PHONY: test-sdk-python
test-sdk-python: ## Python SDK suite
	@cd $(SDK_PY) && collected=$$($(PYTHON) -m pytest tests/ --collect-only -q \
	    -p no:cacheprovider 2>&1 \
	    | grep -oE '[0-9]+ tests? collected' | grep -oE '^[0-9]+' | tail -1); \
	  echo "collected=$${collected:-0} (floor $(FLOOR_SDK_PY))"; \
	  if [ "$${collected:-0}" -lt $(FLOOR_SDK_PY) ]; then \
	    echo "::error::Python SDK collected $${collected:-0} tests, floor is $(FLOOR_SDK_PY)"; \
	    exit 1; \
	  fi
	cd $(SDK_PY) && $(PYTHON) -m pytest tests/ -v

.PHONY: test-sdk-typescript
test-sdk-typescript: ## TypeScript SDK suite
	cd $(SDK_TS) && npx jest --ci --passWithNoTests=false
	@cd $(SDK_TS) && files=$$(npx jest --ci --listTests 2>/dev/null | grep -c 'test\.ts$$' || true); \
	  echo "test files=$${files:-0} (floor $(FLOOR_SDK_TS_FILES))"; \
	  if [ "$${files:-0}" -lt $(FLOOR_SDK_TS_FILES) ]; then \
	    echo "::error::expected at least $(FLOOR_SDK_TS_FILES) TypeScript test files, found $${files:-0}"; \
	    exit 1; \
	  fi

# =============================================================================
# Version
# =============================================================================

.PHONY: version
version: ## Print the version every artifact should state
	@echo $(VERSION)

.PHONY: version-check
version-check: ## Fail if any of the 22 version sites disagrees with VERSION
	$(PYTHON) scripts/version_sync.py --check

.PHONY: version-sync
version-sync: ## Rewrite every version site from VERSION (MODIFIES files)
	$(PYTHON) scripts/version_sync.py

# =============================================================================
# Diagrams
# =============================================================================

.PHONY: diagram
diagram: ## Regenerate the architecture SVGs (light + dark) -- MODIFIES files
	$(PYTHON) scripts/render_architecture.py

.PHONY: diagram-check
diagram-check: ## Fail if the committed architecture SVGs are stale
	$(PYTHON) scripts/render_architecture.py --check

# =============================================================================
# Secrets
# =============================================================================

.PHONY: secrets-scan
secrets-scan: ## Scan tracked history for secrets (gitleaks, full built-in ruleset)
	gitleaks detect --source . --config .gitleaks.toml --redact --verbose

.PHONY: secrets-selftest
secrets-selftest: ## Prove the scanner works: 4 planted secrets found, old config finds 0
	./scripts/gitleaks-selftest.sh

# =============================================================================
# Aggregates
# =============================================================================

.PHONY: gate-check
gate-check: ## Fail if a CI job is not wired into ci-gate
	$(PYTHON) scripts/ci/check_gate_complete.py .github/workflows/ci.yml

.PHONY: verify
verify: version-check diagram-check gate-check lint typecheck secrets-scan secrets-selftest test ## Everything CI runs, minus the Redis suite
	@printf '\n\033[32mverify: OK\033[0m  (for the Redis-backed Rust tests: make redis test-rust-redis)\n'

# =============================================================================
# Local services
# =============================================================================

.PHONY: redis
redis: ## Start the Redis container the Redis-backed Rust tests need
	@docker rm -f octollm-dev-redis >/dev/null 2>&1 || true
	docker run -d --rm --name octollm-dev-redis -p 6379:6379 redis:8-alpine
	@until docker exec octollm-dev-redis redis-cli ping >/dev/null 2>&1; do sleep 0.3; done
	@echo "redis ready on localhost:6379"

.PHONY: redis-stop
redis-stop: ## Stop that Redis container
	docker rm -f octollm-dev-redis

# =============================================================================
# Housekeeping
# =============================================================================

.PHONY: clean
clean: ## Remove build, coverage and test artifacts (never touches tracked files)
	rm -rf $(ORCHESTRATOR)/htmlcov $(ORCHESTRATOR)/coverage.xml $(ORCHESTRATOR)/junit.xml
	rm -rf $(SDK_TS)/dist $(SDK_TS)/coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .ruff_cache .mypy_cache
