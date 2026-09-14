# AGENTS.md

**Forge coding surface for AI agents working in doublegate/OctoLLM.**

This file tells coding agents (CloudAgents, smiths, Artificers) how to work in this repository. Read `CLAUDE.md` and `docs/PROJECT-STATUS.md` for deeper context — this is the distillation.

---

## Job

Build a distributed AI architecture for offensive security and developer tooling, inspired by octopus neurobiology. Keep every claim in the repository either true or deleted — implementation over documentation debt.

**Current stage:** Stage 4 complete (shared arm framework), Stage 5 next (Neural Ring and capability tokens). See twelve-stage roadmap to v1.0.0 in `CLAUDE.md`.

---

## Stack

- **Languages:** Python 3.14 (Poetry), Rust 1.91.1+ (workspace with 5 members), TypeScript (SDK only)
- **Python services:** FastAPI, SQLAlchemy 2.0, Pydantic, structlog
- **Rust services:** Axum (reflex layer), tokio, serde
- **Persistence:** PostgreSQL 17 (global memory), Redis 8 (cache + ring streams), Qdrant 1.12 (vector store)
- **Deployment:** Docker Compose (`compose.yaml`) for local dev; Kubernetes planned for production (Stage 12)
- **Observability:** Prometheus, Grafana, Loki, Jaeger (scaffolded, not yet wired end-to-end)
- **LLM providers:** OpenAI, Anthropic (optional), Ollama (local), FakeProvider (default — **stack runs with NO API KEYS**)

**What exists today:**
- Rust reflex layer (8,500 lines, 241 tests passing, PII/injection detection live)
- FastAPI orchestrator (197 tests, 93% coverage, no execution engine yet — tasks stay `pending`)
- Shared Python framework (`octollm_common`) imported by all 8 arms + orchestrator (103 tests, 95% coverage)
- Six Python arm stubs (each serves `/health`, `/ready`, `/capabilities`, `/metrics`; main endpoint returns 501 naming Stage 8)
- Rust executor arm stub (21 lines; sandbox lands Stage 9)
- Python SDK (28 tests) and TypeScript SDK (28 tests) — both unpublished
- 11-service compose stack that reaches HEALTHY (`make up`)

---

## Commands

**Prefer the Makefile as source of truth.** Every CI job invokes these targets, so local pass = CI pass by construction.

### Install and setup
```bash
make install       # every Python package (editable) + TypeScript SDK
make help          # list all targets
```

### Lint and format
```bash
make lint          # ruff, black, clippy, rustfmt, eslint, tsc, yamllint, shellcheck, actionlint
make format        # MODIFIES files: rewrite Python and Rust in place
make typecheck     # mypy over shared framework, orchestrator, Python SDK
```

### Test
```bash
make test          # all suites: 241 Rust + 103 shared + 197 orchestrator + 28 Python SDK + 28 TS SDK
make test-rust     # Rust workspace tests
make test-shared   # shared arm framework, 90% coverage floor
make test-orchestrator  # orchestrator, 85% coverage floor
make test-sdk-python    # Python SDK
make test-sdk-typescript # TypeScript SDK

# Redis-backed Rust tests (needs Redis on :6379)
make redis && make test-rust-redis && make redis-stop
```

### Aggregates
```bash
make verify        # everything ci-gate runs: version-check, lint, typecheck, all suites (minus Redis suite)
make version-check # fail if any of 24 version sites disagrees with VERSION file
make version-sync  # MODIFIES: rewrite every version site from VERSION
make secrets-scan  # gitleaks over tracked history
make secrets-selftest  # prove scanner works: 4 planted secrets found, old config finds 0
```

### The stack
```bash
make up            # build and start all 11 services; waits for HEALTHY (not just "started")
make smoke         # assert stack is healthy and a task round-trips (stays `pending` — correct until Stage 7)
make ps            # show each service and its health
make logs          # follow logs of every service
make down          # stop and remove volumes
```

**No API keys needed.** Host ports overridable: `REFLEX_PORT=18080 make up`.

### Versioning and diagrams
```bash
make version       # print the version (from VERSION file: currently 0.5.0)
make diagram       # MODIFIES: regenerate architecture SVGs (light + dark)
make diagram-check # fail if committed SVGs are stale
```

---

## Test how-to

See `.github/workflows/ci.yml` — it invokes Makefile targets, and those targets enforce collection floors.

**Rust:** `cargo test --workspace --all-features` (241 tests). Redis-backed tests: `cargo test -- --ignored` (18 tests, need Redis on :6379).

**Python:** pytest with coverage floors enforced by each suite's `pytest.ini` or `pyproject.toml`:
- Shared framework: 90% coverage floor, 103 tests minimum
- Orchestrator: 85% coverage floor, 197 tests minimum
- Python SDK: 28 tests minimum

**TypeScript SDK:** `npx jest --ci --passWithNoTests=false`, 3 test files minimum.

Every suite asserts a collection floor because a suite silently collecting zero tests produces the same green check as one that ran them all.

---

## PR norms

### Branch naming
All agent branches: `cursor/<descriptive-name>-953d`

Examples:
- `cursor/fix-reflex-cache-race-953d`
- `cursor/add-capability-tokens-953d`
- `cursor/stage-8-python-arms-953d`

### Draft PR → Artificer verify → Luke merges only

1. **Open as draft PR by default** unless user explicitly requests otherwise
2. **Run `make verify` locally** before pushing (or let CI catch it)
3. **Commit and push incrementally** as you implement → test → fix
4. **Create/update PR at end of turn** if you made changes this turn
5. **Mark ready for review** only when implementation complete, tests passing, `make verify` green
6. **Luke merges** — bots/CloudAgents/smiths open PRs only; never self-merge, never push `--auto` flag

### PR requirements
- All CI checks passing (eleven jobs aggregated by `ci-gate`)
- Tests included for new code (coverage floors enforced)
- Documentation updated if functionality changes
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `ci:`, `build:`, `chore:`
- No secrets committed (gitleaks scans full history)

**Do NOT merge** unless Luke explicitly approves. **Do NOT DM Luke from smiths** — use PR comments or the task thread.

---

## Secrets hygiene

### Stack runs with NO API KEYS
`compose.yaml` environment variables for `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are empty by default. The LLM provider defaults to `FakeProvider` (deterministic, never calls a model). This is what makes the entire test suite run without credentials.

### Never commit secrets
- `.env` files with real credentials are gitignored — never commit them
- Use placeholders in examples: `YOUR_API_KEY`, `EXAMPLE_KEY_abc123xyz`, `CHANGE_ME_...`
- Known-fake values exempted in `.gitleaks.toml` individually, by value, anchored `^...$`
- **Never add path exemptions** to `.gitleaks.toml` — the old config exempted all `.md` files and `docs/`/`tests/` dirs, scanning almost nothing

### Scrub secrets from prompts and logs
- PII detection at reflex layer screens SSN, credit cards, API keys in patterns
- Safety Guardian arm screens egress (output leaving the system)
- Never log raw user input without sanitization
- `structlog` JSON format for aggregation, but redact before shipping

### Pre-commit and CI enforcement
```bash
pre-commit install          # runs gitleaks, ruff, black, mypy on every commit
make secrets-scan           # gitleaks over tracked history
make secrets-selftest       # prove scanner finds 4 planted secrets; old config finds 0
```

`.gitleaks.toml` runs with `[extend] useDefault = true` — **do not remove that line**. Without it, adding a custom `[[rules]]` block silently discards all ~170 built-in rules.

---

## Luke-merge rule

**Bots and CloudAgents open PRs only. Luke merges (or explicitly delegates).**

This repository is under active correctness work — Stages 0-4 fixed CI that could not fail, a Makefile that didn't exist, secret scanning that exempted everything, and 23 compose variables silently ignored. That history means:

- **Do not self-merge** even if you have write access
- **Do not enable auto-merge** (`gh pr merge --auto` or UI toggle)
- **Do not force-push** or amend commits unless explicitly instructed
- **Do not leave `main` branch** unless user explicitly asks

If Luke says "ship it" or "LGTM, merge when green," that is explicit approval to merge. Otherwise, PRs stay open for human review.

**Smiths (Kingdom forge bots):** Do not DM Luke. Use PR comments or the task thread. Luke reviews the queue; pinging outside the forge flow creates out-of-band state.

---

## Verification

### Require real evidence
- **Tests passing** (see collection floors above)
- **CI green** (eleven jobs in `ci-gate`, no `continue-on-error` anywhere)
- **Compose health** (`make up && make smoke` — all services HEALTHY, task round-trips)
- **Not "it should work"** — show the test output, the CI link, the service logs

### Implementer ≠ reviewer
Agent that writes code ≠ agent that merges. This is defense-in-depth for the forge:
- Outer agent (you) implements and verifies locally
- Inner agent (Artificer, if invoked) reviews against spec
- Luke merges after human review

### Kingdom forge patterns
If you are a Kingdom forge bot (Cursor CloudAgent, smith, Artificer):

- **sand-workflow:forge-verification-exit** — require CI green + smoke test + tests added before marking PR ready
- **sand-workflow:outer-inner-cloud-agent** — outer agent implements, inner agent (Artificer) reviews code diffs and correctness against requirements
- Both patterns documented in Kingdom skills; use them when the task scale justifies the overhead

For small fixes (typo, version bump, doc clarification), full outer-inner overhead is not needed — just verify `make verify` passes and open the PR.

---

## Skill diet

### Coding bots: minimal, targeted skill set

When working in this repository, prefer **built-in tools + these skills**:

1. **Code changes** — the tools you have (Read, Write, StrReplace, Shell, Grep, Glob)
2. **verification-before-completion** — always verify (tests, CI, compose health) before marking done
3. **Context7 MCP** — when you need current library docs (FastAPI, SQLAlchemy, Pydantic, Axum, tokio, etc.)

**Do NOT flood with marketplace skills.** No pstack dump, no superpowers grab-bag, no 15-skill import for a 3-line change. Marketplace skills are for vertical workflows (e.g., Sentry for error triage, Linear for issue handoff, Slack for thread sync). This is a coding repo; you already have coding tools.

### AGENTS.md is the always-on framework

This file (`AGENTS.md`) **is always applied** to agents working here. It is not a skill you fetch; it is the base truth for this repository. Skills are additive when a workflow (e.g., release pipeline, compliance audit, customer handoff) needs domain-specific context beyond "write and verify code."

### When to reach for a skill

- **Sentry-debug-issue** — if user links a Sentry error and asks you to fix root cause
- **Linear integration** — if user asks you to create/update a Linear issue with findings
- **Notion knowledge-capture** — if user asks to persist analysis as a Notion page
- **Verification patterns** (outer-inner, forge-verification-exit) — when task is multi-stage with explicit verification gates

For a PR that adds a feature, fixes a bug, or updates docs? You do not need a skill. `make verify` and this file are enough.

---

## Summary

- **Job:** Build OctoLLM (distributed AI, octopus-inspired). Make claims true or delete them.
- **Stack:** Python 3.14 + Poetry, Rust workspace, TypeScript SDK, FastAPI, Docker Compose, **no API keys needed**.
- **Commands:** `make install`, `make verify`, `make test`, `make up` (see Makefile for full list).
- **Tests:** CI enforces collection floors; suites are Rust (241), shared (103), orchestrator (197), SDKs (28+28).
- **PRs:** Branch `cursor/*-953d`, draft by default, Artificer verify if needed, **Luke merges only**.
- **Secrets:** Stack runs keyless; gitleaks scans history; never commit `.env` with real creds; no path exemptions.
- **Verification:** Real evidence required (tests green, CI green, `make smoke` passes). Implementer ≠ merger.
- **Skills:** Code-changes + verification-before-completion + Context7 when needed. No marketplace flood.

**Questions?** Read `CLAUDE.md` (how to work here) and `docs/PROJECT-STATUS.md` (where the project is). Both are more detailed than this file and stay current with stage progress.
