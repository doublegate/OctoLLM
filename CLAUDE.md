# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**OctoLLM** is a distributed AI architecture for offensive security and developer tooling, inspired by octopus neurobiology. Implementation is underway: a Rust workspace (reflex layer, executor arm, three shared crates), a Python FastAPI orchestrator, six arm service images, and Python + TypeScript SDKs all exist alongside the architectural documentation.

### Core Concept

The system mirrors the octopus's distributed nervous system where:
- **Central Brain (Orchestrator)**: Strategic planning and coordination using frontier LLMs (GPT-4, Claude Opus)
- **Autonomous Arms (Specialized Modules)**: Domain-specific execution with local decision-making
- **Reflex Layer**: Fast preprocessing for common patterns without LLM involvement
- **Distributed Memory**: Global semantic memory + local episodic stores per arm

### Key Architectural Principles

1. **Modular Specialization**: Each component excels at one thing
2. **Distributed Autonomy with Centralized Governance**: Arms decide locally, brain coordinates globally
3. **Defense in Depth**: Multiple security layers (reflex preprocessing, capability isolation, PII sanitization)
4. **Hierarchical Processing**: Expensive resources reserved for complex problems
5. **Active Inference**: System proactively reduces uncertainty rather than waiting for instructions

## Documentation Structure

### Primary References (read these first)

- `ref-docs/OctoLLM-Project-Overview.md` - Strategic vision, biological inspiration, use cases, success metrics, roadmap
- `ref-docs/OctoLLM-Architecture-Implementation.md` - Technical blueprint, component specs, deployment patterns, code examples
- `ref-docs/OctoLLM-Concept_Idea.md` - Quick-start patterns and concrete design decisions

### Understanding the Architecture

**Layer 1: Ingress** (API Gateway + Reflex)
- Technology: NGINX/Traefik + Python/Rust for reflex logic
- Latency Target: <10ms for cache hits, <50ms for reflex decisions

**Layer 2: Orchestration** (The Brain)
- Technology: Python + FastAPI, LangChain/LlamaIndex
- Main Loop: Cache check → Plan generation → Step execution → Result integration → Validation

**Layer 3: Execution** (The Arms)
- **Planner Arm**: Task decomposition (Python, uses GPT-3.5-turbo)
- **Tool Executor Arm**: External actions in sandboxed environments (Rust for safety)
- **Retriever Arm**: Knowledge base search
- **Coder Arm**: Code generation, debugging, refactoring
- **Judge Arm**: Output validation and quality assurance
- **Safety Guardian Arm**: PII detection, content filtering

**Layer 4: Persistence**
- PostgreSQL (global memory), Redis (caching), Qdrant/Weaviate (vector stores)

**Layer 5: Observability**
- Prometheus (metrics), Loki (logs), Jaeger (tracing)

## Key Data Structures

**TaskContract** (core orchestration object):
- `task_id`: Unique identifier
- `goal`: Natural language description
- `constraints`: Hard constraints (time, cost, safety)
- `context`: Background information
- `acceptance_criteria`: Success conditions
- `budget`: Resource limits (tokens, time)
- `assigned_arm`: Target arm identifier

**ArmCapability** (arm registry):
- `arm_id`, `name`, `description`
- `input_schema`, `output_schema`: JSON schemas
- `capabilities`: Tags for routing (e.g., "code", "security")
- `cost_tier`: 1 (cheap) to 5 (expensive)
- `endpoint`: Kubernetes service URL

## Development Roadmap

**Phase 1: Proof of Concept** (Months 1-2) - IN PROGRESS
- Reflex preprocessing layer
- Orchestrator (basic planning/delegation)
- Two arms: Planner + Tool Executor
- Docker Compose deployment

**Phase 2: Core Capabilities** (Months 3-5)
- Additional arms: Retriever, Coder, Judge, Safety Guardian
- Kubernetes deployment
- Distributed memory system
- Swarm decision-making

**Phase 3: Optimization** (Months 6-9)
- Rust reimplementation of performance-critical arms
- Fine-tuned specialist models
- Skill distillation

**Phase 4: Production Hardening** (Months 10-12)
- Comprehensive observability
- SOC 2 / ISO 27001 compliance
- Public API and documentation

## When Implementing Components

### Technology Choices

**Orchestrator (Brain)**:
```python
# Python 3.11+, FastAPI, Pydantic
# LLM: OpenAI SDK (GPT-4) or Anthropic SDK (Claude 3)
# Dependencies: langchain, redis, psycopg, prometheus-client, structlog
```

**Reflex Layer (Performance-Critical)**:
```rust
// Rust 1.75+, actix-web
// Redis for caching, regex for PII/injection detection
// Target: <10ms latency for 95% of requests
```

**Arms (Mixed)**:
- Python for AI-heavy arms (Planner, Coder, Judge)
- Rust for security-critical arms (Tool Executor)
- Small models (Mistral 7B, GPT-3.5-turbo) for cost efficiency

### Security Patterns

1. **Capability-Based Access**: Each arm gets time-limited tokens for specific permissions
2. **Sandboxing**: Tool Executor runs in isolated containers (Docker/gVisor)
3. **PII Protection**: Input sanitization, output filtering, differential privacy
4. **Allowlisting**: Commands and hosts explicitly permitted
5. **Provenance Tracking**: Every artifact tagged with source, timestamp, confidence

### Deployment

- **Local Dev**: `docker-compose.yml` with all services
- **Production**: Kubernetes with namespace `octollm`
- **Monitoring**: Prometheus + Grafana dashboards
- **Scaling**: HorizontalPodAutoscaler based on CPU/memory

## Testing Strategy

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires services)
docker-compose up -d
pytest tests/integration/ -v

# Coverage
pytest --cov=orchestrator --cov=arms --cov-report=html
```

## Key Metrics to Track

| Metric | Target |
|--------|--------|
| Task Success Rate | >95% vs baseline |
| P99 Latency | <30s for critical tasks |
| Cost per Task | <50% of monolithic LLM |
| Reflex Cache Hit Rate | >60% over time |
| PII Leakage Rate | <0.1% of outputs |
| Prompt Injection Blocks | >99% detection |

## Important Conventions

1. **JSON Schemas**: All arm inputs/outputs validated with Pydantic schemas
2. **Provenance Metadata**: Always include `arm_id`, `timestamp`, `confidence`, `command_hash`
3. **Error Handling**: Retry logic with exponential backoff, graceful degradation
4. **Resource Limits**: Enforce timeouts (default 30s max) and token budgets
5. **Logging**: Structured logging with `structlog` (JSON format for aggregation)

## Design Patterns in Use

1. **Mixture of Experts (MoE)**: Multiple specialists with gating function
2. **Swarm Decision-Making**: N parallel proposals → aggregation → conflict resolution
3. **Hierarchical Planning**: Recursive task decomposition with acceptance criteria
4. **Active Inference Loops**: Observe → Hypothesize → Predict → Act → Update
5. **Skill Distillation**: Fine-tune smaller models from decision traces

## Future Implementation Notes

- Use LangGraph or custom state machine for workflow orchestration
- Abstract LLM calls behind provider-agnostic interface (support OpenAI, Anthropic, local models via vLLM/Ollama)
- Implement uncertainty-based routing (ML classifier predicts best arm from task features)
- Add distributed tracing with OpenTelemetry for debugging complex flows
- Consider speculative execution (predict next arm in parallel)

## Current Status

Implementation is underway. This is no longer a documentation-only repository.

### What exists

| Area | Location | State |
|---|---|---|
| Rust workspace | `Cargo.toml` (5 members) | `reflex-layer`, `arms/executor`, `shared/rust/{common,types,clients}`; 240 tests passing |
| Orchestrator | `services/orchestrator/` | FastAPI app, SQLAlchemy models, Reflex client with circuit breaker, arm registry; 186 tests passing |
| Shared framework | `shared/python/octollm_common/` | App factory, error envelope, contract models, arm roster, LLM providers; 103 tests |
| Arm images | `services/arms/{coder,judge,planner,retriever,safety_guardian}/` | Built on the shared framework; each arm's own endpoint returns 501 naming Stage 8 |
| Python SDK | `sdks/python/octollm-sdk/` | 8 service clients; 28 tests passing |
| TypeScript SDK | `sdks/typescript/octollm-sdk/` | 8 service clients; 28 tests passing |

### Toolchain

- **Python 3.14** (`>=3.14,<3.15` at the root; the `<3.15` bound comes from presidio).
  Service images are `python:3.14.7-slim`.
- **Rust** edition 2021, MSRV 1.91.1; builder images are `rust:1.98.1-slim`, runtime
  `debian:13.6-slim`.
- Poetry for the root Python environment; `services/orchestrator/` and each SDK carry
  their own manifest.

### Commands

**Use the Makefile.** Every check is a make target and **every CI job invokes that
target**, so a local pass and a CI pass mean the same thing by construction. Running the
underlying commands by hand is fine for a tight loop, but the target is the contract.

```bash
make help              # every target, self-documenting
make install           # every Python package (editable) + the TypeScript SDK
make verify            # everything ci-gate runs: version-check, lint, typecheck, all suites
make format            # rewrite Python and Rust in place (the only target that MODIFIES)

# Individual gates
make lint-python lint-rust lint-typescript lint-config
make typecheck
make sdk-parity-check  # both SDKs agree, and call only routes that exist
make test              # 240 Rust + 103 shared + 186 orchestrator + 28 Python SDK + 28 TypeScript SDK

# The one suite `make verify` leaves out (needs Redis on :6379)
make redis && make test-rust-redis && make redis-stop
```

Targets for things that do not work yet (`up`, `smoke`, `eval`, `release-gate`) are
**deliberately absent rather than stubbed** — they arrive with the stages that make them
true (compose in Stage 3, evals in Stage 10, release in Stage 12). Do not add a target
that does not work; that is the failure this repository is being dug out of.

### Running the stack

```bash
make up      # all 11 services, waits for HEALTHY (not merely "started")
make smoke   # asserts health + that a task round-trips
make down
```

**No API keys needed.** Host ports are overridable if one is taken: `REFLEX_PORT=18080 make up`.

Three invariants the gates enforce, each of which was violated before Stage 3:

- **Every compose variable must be one the service reads.** All 23 were silently ignored —
  the orchestrator needs the `ORCHESTRATOR_` prefix, the reflex layer needs
  `REFLEX_<SECTION>__<FIELD>` with a *double* underscore. `make compose-env-check`.
- **One canonical port map.** `scripts/ci/check_port_map.py` is authoritative, and the
  Dockerfile plus compose file win over any spec, because they are what binds a socket.
  Every arm's OpenAPI spec previously named its neighbour's port. `make port-map-check`.
- **`make smoke` asserts the task stays `pending`.** That is correct until Stage 7 builds
  the execution engine; do not "fix" it to `completed` before the engine exists.

Contract: `docs/api/CONTRACT.md`. Wire format is snake_case including enum values, with
acronyms pinned (`ssn`, not `s_s_n`). Reflex fixtures are **captured from the running
service** by `scripts/capture_reflex_fixtures.py` — never hand-written, which is how a
client that could not parse a single real response kept 39 tests green.

### Secret scanning

`.gitleaks.toml` runs with `[extend] useDefault = true` — **do not remove that line**.
Gitleaks replaces its ~170 built-in rules when a config declares `[[rules]]`, so
without it, adding a custom rule silently removes 170.

**No path is exempt except generated and vendored trees.** Known-fake values are
exempted individually, by value, anchored `^…$`. If a documentation example trips the
scanner, use a sanctioned placeholder (`YOUR_…`, `…EXAMPLE…`, `CHANGE_ME_…`, or an
elided `…abc…`) or add one anchored literal with a comment — **never add a path**.
The previous config exempted every `.md` file, all of `docs/`/`tests/`,
`.github/workflows/*.yml` and `infrastructure/*.sh`, and had been reporting clean for
months while inspecting almost nothing.

```bash
make secrets-scan        # gitleaks over tracked history
make secrets-selftest    # plants 4 secrets; asserts this config finds all 4
                         # AND that the old config finds 0
```

That second assertion is why the self-test means anything: a scan of nothing reports
exactly what a clean scan reports.

### Versioning

`VERSION` at the repository root is the single source of truth, propagated to **24 sites**
by `scripts/version_sync.py` and enforced by `make version-check`. Before it existed those
those sites held six different answers at once, three of them reachable at runtime: `/health`
reported `0.1.0` while spans reported `0.9.0` while the README badge said `1.2.0`.

Current version is **0.5.0**, and it is the first number here that is true everywhere.
The repository has **zero git tags** and neither SDK exists on PyPI or npm, so every
earlier number — including the 13 releases in `CHANGELOG.md` — was a claim about an
artifact that was never built. `1.0.0` is cut at Stage 12. Rationale: `docs/adr/008`.

To bump: `echo X.Y.Z > VERSION && make version-sync`, then commit. Never write a version
literal into a test — assert against `__version__`.

### What CI does and does not cover

`ci.yml` is the blocking gate. It replaced `lint.yml` and `test.yml`, which between them
could not fail: every test step was `|| echo "No tests found yet (Phase 0)"` *and*
`continue-on-error: true`, and the summary job announced "Phase 0: No tests exist yet"
over 240 Rust and 178 Python tests that CI never ran.

Eleven jobs, all blocking, all aggregated by `ci-gate` — **make `ci-gate` the only required
check in branch protection**:

| Job | Covers |
|---|---|
| `lint-python` | ruff, black |
| `typecheck-python` | mypy, against real installed dependencies (**blocking**) |
| `lint-rust` | `cargo fmt`/`clippy` at **workspace** scope, including the three `shared/rust` crates |
| `lint-typescript` | eslint, tsc |
| `lint-config` | yamllint, OpenAPI validity, shellcheck, actionlint |
| `test-rust` | 240 workspace tests + the 17 Redis-backed ones against a `redis:8-alpine` service |
| `test-shared` | 103 tests, coverage floored at 90%; provider extras deliberately NOT installed |
| `test-orchestrator` | 186 tests, coverage floored at 85% by its own pytest config |
| `test-sdk-python` | 28 tests |
| `test-sdk-typescript` | 28 tests |

Three invariants hold and are enforced rather than remembered:

- **No `continue-on-error`, no `|| echo`.** A gate that cannot fail is indistinguishable
  from one that passed.
- **Every suite asserts a collection floor** (103 / 186 / 28 / 28 / 18). A suite that silently
  collects zero tests produces the same green check as one that ran them all. Raise a
  floor when you add tests; never lower one.
- **`scripts/ci/check_gate_complete.py` fails if a job is added to `ci.yml` without being
  added to `ci-gate.needs`.** Otherwise a new job is advisory by omission — it can fail
  while the gate goes green.

Still outside the gate, deliberately:

- **Container builds** (`build.yml`) and the Trivy container scan (`security.yml`) are
  gated on the `ENABLE_IMAGE_PUBLISH` / `ENABLE_CONTAINER_SCAN` repository variables,
  which are unset. Five service Dockerfiles still `CMD` into modules that do not exist,
  so those images cannot pass a smoke test yet. Build locally before merging a Dockerfile
  change. They join `ci-gate` once the services they build are real.
- **CodeQL** runs through GitHub's **default setup**, not a workflow in this repository.
  Default setup is already configured for actions, javascript/typescript, python and rust
  on a weekly schedule, and an advanced-setup workflow cannot coexist with it — GitHub
  refuses SARIF from an advanced configuration while default setup is enabled. Its query
  suite is `default`; raising it to `extended` (the equivalent of `security-and-quality`)
  is a repository-settings change, not a code change.
- **Snyk** stays advisory; it is skipped entirely without `SNYK_TOKEN`.

### The shared arm framework

`shared/python/octollm_common` is imported by all eight arms **and** the orchestrator, so
a change here is a change to nine services. It is installed by `make install`; the
container images reach it through `PYTHONPATH=/app/shared/python`.

Four seams live there, and each exists because its absence produced a real defect:

- **`models/contracts.py`** — every arm's request and response models, defined once. The
  arms use them as FastAPI models and the orchestrator imports the same classes. Do not
  add a second definition: the reflex client and the reflex layer kept separate
  definitions of one payload, disagreed on four fields, and the client could not parse a
  single real response while 39 of its tests passed against mocks built from its own
  models.
- **`roster.py`** — the eight arms, declared once. Each arm's `main.py` reads its spec
  from here, the orchestrator's registry reads the whole roster, and
  `check_port_map.py` checks it against what actually binds.
- **`errors.py`** — one envelope for all nine services, `RequestValidationError`
  included. Never return a bare `{"detail": ...}`.
- **`llm/`** — `create_provider()` returns `FakeProvider` unless a provider is
  explicitly configured, and **`OCTOLLM_FORCE_FAKE_LLM=1` overrides configuration
  entirely**, which is what makes it impossible for a test to reach a model. A missing
  key raises rather than falling back to the fake: a deployment that believes it is
  calling a real model and is not would be far worse than one that refuses to start.
  The provider SDKs are optional extras, so CI installs none of them and the adapter
  tests substitute fake modules in `sys.modules`.

### Both SDKs are checked against reality

`make sdk-parity-check` derives what each service serves from the code that serves it
(the orchestrator's route table, the roster plus the framework paths, the Rust
`.route(...)` calls) and asserts both SDKs call the same set, that every call resolves
or is listed with the stage that will build it, and that each framework arm's OpenAPI
spec documents exactly what it serves.

Every SDK test mocks the transport, which is why four broken calls survived 56 green
tests — a mock is built from the same wrong belief as the client. Do not "fix" a parity
failure by adding a PENDING entry for a path that is simply wrong.

### Known gaps

- `services/orchestrator/pyproject.toml` declares the OpenTelemetry dependencies that
  `app/telemetry.py` imports, but the orchestrator image installs the **root**
  `pyproject.toml`, which does not. The two manifests need reconciling before that image
  can serve traced traffic.
- The six Python arms answer their own endpoint with 501. Stage 8 implements them.
