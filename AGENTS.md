<!-- Managed by Master-Claude. Universal rules come from the imported/inlined core.
     Edit only inside the MC-PROJECT block; mc-sync overwrites everything else. -->
<!-- mc-core: 0.2.0 | mode=import | lang=rust -->
# AGENTS.md — OctoLLM

@/home/parobek/.claude/master-core/AGENTS.base.md
@/home/parobek/.claude/master-core/lang/rust.md
@/home/parobek/.claude/master-core/modules/10-commits-and-versioning.md
@/home/parobek/.claude/master-core/modules/20-testing-and-accuracy.md
@/home/parobek/.claude/master-core/modules/30-quality-gates.md
@/home/parobek/.claude/master-core/modules/40-docs-and-adrs.md
@/home/parobek/.claude/master-core/modules/50-architecture-patterns.md
@/home/parobek/.claude/master-core/modules/60-security.md
@/home/parobek/.claude/master-core/modules/70-release-ceremony.md
@/home/parobek/.claude/master-core/modules/80-phase-sprint-workflow.md
@/home/parobek/.claude/master-core/modules/90-multi-language-integration.md
@/home/parobek/.claude/master-core/modules/91-agent-system-architecture.md
@/home/parobek/.claude/master-core/modules/95-named-pattern-library.md

<<< MC-PROJECT-START >>>
## Project: OctoLLM

> ## Read `docs/PROJECT-STATUS.md` first
>
> This file is **how to work here** — commands, conventions, and invariants.
> [`docs/PROJECT-STATUS.md`](docs/PROJECT-STATUS.md) is **where the project is** — what
> runs today, what is deliberately not true yet, which stage is next, and which
> decisions are waiting on a human.
>
> Both matter, and the status file changes far more often. Read it at the start of every
> session, and update it in the same change as anything that makes one of its numbers
> wrong.
>
> **The governing rule of this repository: every claim in it is either made true or
> deleted.** It spent its first phase describing a system that had not been built, with
> nothing in CI able to contradict it. Do not add a make target that does not run, a
> document that states an intention as a fact, or a test that cannot fail.

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

The repository carries 340 tracked markdown files, **most written ahead of the code**.
Reconciling them is Stage 12. Until then only six are authoritative:

| File | Holds |
|---|---|
| `docs/PROJECT-STATUS.md` | current state — read first |
| `AGENTS.md` (this file) | how to work here: commands, conventions, invariants |
| `docs/api/CONTRACT.md` | the frozen API contract |
| `CHANGELOG.md` | user-visible change, under `[Unreleased]` |
| `docs/adr/` | decisions, in Nygard format |
| `README.md` | the public front door |

**If a document and the code disagree, the code wins and the document is the bug.**

Known stale — do not act on these without checking the code: `docs/src/project-tracking/status.md`
("22% complete", "v1.2.0", dated 2025-11-15), `to-dos/status/` (32 files, three reporting on
the same sprint), `to-dos/MASTER-TODO.md` (the earlier seven-phase roadmap — history, not a
plan), and anything under `docs/book/` (a committed build artifact).

### Design references (pre-code intent, not current state)

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

This is the long-horizon capability plan. The **executing** plan is the 12-stage map in
`docs/PROJECT-STATUS.md`, which is the single source of truth for what is done; never
restate a stage's status here.

**Phase 1: Proof of Concept** (Months 1-2)
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

Versions live in **### Toolchain** below — do not restate them here.

**Orchestrator (Brain)**:
```python
# FastAPI, Pydantic
# LLM: OpenAI SDK (GPT-4) or Anthropic SDK (Claude 3)
# Dependencies: langchain, redis, psycopg, prometheus-client, structlog
```

**Reflex Layer (Performance-Critical)**:
```rust
// actix-web
// Redis for caching, regex for PII/injection detection
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

### What exists

Stage progress lives in `docs/PROJECT-STATUS.md` and nowhere else. This table is
orientation — which tree holds what — not a status report.

| Area | Location | State |
|---|---|---|
| Rust workspace | `Cargo.toml` (5 members) | `reflex-layer`, `arms/executor`, `shared/rust/{common,types,clients}`; 241 tests + 18 `#[ignore]`d Redis-backed |
| Reflex layer | `reflex-layer/` (`:8080`) | Implemented. PII + prompt-injection detection, Redis cache, token-bucket rate limiting; `POST /process` works |
| Orchestrator | `services/orchestrator/` (`:8000`) | FastAPI app, SQLAlchemy models, Reflex client with circuit breaker, arm registry, capability signing authority; 225 tests. **It does not call any arm** — Stage 7 |
| Shared framework | `shared/python/octollm_common/` | App factory, error envelope, contract models, arm roster, LLM providers, **capability tokens, the Neural Ring, peer clients**; 210 tests |
| Python arms | `services/arms/{planner,retriever,coder,judge,safety_guardian}/` (`:8001`–`:8005`) | Scaffolded on the shared framework; serve `/health`, `/ready`, `/capabilities`, `/metrics`. Each arm's own endpoint returns 501 naming Stage 8 |
| Executor arm | `services/arms/executor/` (`:8006`, host `:18006`) | Rust stub, `/health` only. Sandbox is Stage 9 |
| Memory / Curator, Red Team | `:8007`, `:8008` | Not built (Stages 6 and 11). The roster declares all eight arms |
| Python SDK | `sdks/python/octollm-sdk/` | 8 service clients; 28 tests passing |
| TypeScript SDK | `sdks/typescript/octollm-sdk/` | 8 service clients; 28 tests passing |

750 tests total. PostgreSQL, Redis and Qdrant run in the stack; **nothing reads or writes
Qdrant** until Stage 6.

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
make verify            # everything ci-gate runs: version-check, diagram-check, gate-check,
                       # compose-env-check, port-map-check, sdk-parity-check, lint,
                       # typecheck, secrets-scan, secrets-selftest, every suite
make format            # rewrite Python and Rust in place (the only target that MODIFIES)

# Individual gates
make lint-python lint-rust lint-typescript lint-config
make typecheck
make gate-check        # every ci.yml job is wired into ci-gate.needs
make sdk-parity-check  # both SDKs agree, and call only routes that exist
make test              # 241 Rust + 210 shared + 225 orchestrator + 28 Python SDK + 28 TypeScript SDK

# Redis on :6379 is required by `make test-shared` (the Neural Ring tests run
# against a real one) and by the Redis-backed Rust suite, which `verify` omits.
make redis && make verify && make test-rust-redis && make redis-stop

```

`make test-shared` **refuses to run** without Redis rather than letting the ring tests
skip. A skipped suite reports exactly what a passing one reports, which is the defect
this repository is being dug out of.

`eval` and `release-gate` do not exist yet and are **deliberately absent rather than
stubbed** — they arrive with the stages that make them true (evals in Stage 10, release in
Stage 12). Do not add a target that does not work; that is the failure this repository is
being dug out of.

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
over the 240 Rust and 178 Python tests that existed at the time and CI never ran.

Eleven jobs, all blocking, all aggregated by `ci-gate` — **make `ci-gate` the only required
check in branch protection**:

| Job | Covers |
|---|---|
| `lint-python` | ruff, black |
| `typecheck-python` | mypy, against real installed dependencies (**blocking**) |
| `lint-rust` | `cargo fmt`/`clippy` at **workspace** scope, including the three `shared/rust` crates |
| `lint-typescript` | eslint, tsc |
| `lint-config` | yamllint, OpenAPI validity, shellcheck, actionlint |
| `test-rust` | 241 workspace tests + the 18 Redis-backed ones against a `redis:8-alpine` service |
| `test-shared` | 210 tests, coverage floored at 90%, against a `redis:8-alpine` service; provider extras deliberately NOT installed |
| `test-orchestrator` | 225 tests, coverage floored at 85% by its own pytest config |
| `test-sdk-python` | 28 tests |
| `test-sdk-typescript` | 28 tests |
| `secrets` | `make secrets-scan` + `make secrets-selftest` over tracked history |

Three invariants hold and are enforced rather than remembered:

- **No `continue-on-error`, no `|| echo`.** A gate that cannot fail is indistinguishable
  from one that passed.
- **Every suite asserts a collection floor** (210 / 225 / 28 / 28 / 18). A suite that silently
  collects zero tests produces the same green check as one that ran them all. Raise a
  floor when you add tests; never lower one.
- **`scripts/ci/check_gate_complete.py` fails if a job is added to `ci.yml` without being
  added to `ci-gate.needs`.** Otherwise a new job is advisory by omission — it can fail
  while the gate goes green.

Still outside the gate, deliberately:

- **Container builds** (`build.yml`) and the Trivy container scan (`security.yml`) are
  gated on the `ENABLE_IMAGE_PUBLISH` / `ENABLE_CONTAINER_SCAN` repository variables,
  which are unset — there is no release to publish until Stage 12. The images themselves
  build and run (`make up` reaches HEALTHY on all eleven services), but nothing in
  `ci-gate` builds them, so **build locally before merging a Dockerfile change**.
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
- **`capability.py` + `security.py`** — capability tokens and `RequireCapability`,
  the callee-side gate. The orchestrator is the **sole signing authority**; no arm mints
  a token. A grant names one callee (`aud`), one task, one scope, and a call budget the
  **callee counts** — a bound the caller is trusted to respect is a request, not a bound.
  TTL is capped at 120s. Never widen a grant to make a test pass; add the edge to the
  roster, where it is reviewed.
- **`ring.py` + `peer.py`** — the Neural Ring. Artifacts go on Redis Streams within the
  types an arm declares in `publishes`/`subscribes`; the tight loops (Coder↔Judge) go
  over capability-gated HTTP. **Ring handlers must be idempotent**: delivery is
  at-least-once and redelivery is normal operation, not an incident. An arm that calls a
  peer returns **cumulative** `usage`, because the orchestrator cannot see that call any
  other way.
- **`llm/`** — `create_provider()` returns `FakeProvider` unless a provider is
  explicitly configured, and **`OCTOLLM_FORCE_FAKE_LLM=1` overrides configuration
  entirely**, which is what makes it impossible for a test to reach a model. A missing
  key raises rather than falling back to the fake: a deployment that believes it is
  calling a real model and is not would be far worse than one that refuses to start.
  The provider SDKs are optional extras, so CI installs none of them and the adapter
  tests substitute fake modules in `sys.modules`.

### Capability tokens: the one rule that is easy to get wrong

**Authorization reads the static roster (`octollm_common.roster.SPECS`), never the live
registry.** `ArmRegistry` accepts `peers` from an arm's own `/capabilities` response --
it has to, since its job is to report what each arm says about itself -- which makes that
field arm-controlled data. An arm that has been compromised could answer its next probe
with `peers: ["executor"]` and, if the issuer trusted the registry, mint itself a path to
the sandbox.

The registry answers *"is the Judge healthy"*. It never answers *"may the Coder call the
Judge"*. A test performs the attack and asserts the refusal; do not "fix" it by reading
`registry.get(arm).peers`.

Two more that follow from the same reasoning:

- **There is no endpoint that issues a capability token.** One that mints authority for
  whoever asks is an endpoint an attacker asks nicely. Operators use
  `scripts/mint_capability.py`, which needs the signing secret.
- **The secret is validated at construction**, so a service with a placeholder secret
  fails to start. One that starts and fails on the first real request has already
  reported itself healthy.

`ORCHESTRATOR_CAPABILITY_SECRET` is unset by default and every capability-gated endpoint
then answers 503. That is the correct default, not a gap. Rationale: `docs/adr/010`.

### Both SDKs are checked against reality

`make sdk-parity-check` derives what each service serves from the code that serves it
(the orchestrator's route table, the roster plus the framework paths, the Rust
`.route(...)` calls) and asserts both SDKs call the same set, that every call resolves
or is listed with the stage that will build it, and that each framework arm's OpenAPI
spec documents exactly what it serves.

Every SDK test mocks the transport, which is why four broken calls survived 56 green
tests — a mock is built from the same wrong belief as the client. Do not "fix" a parity
failure by adding a PENDING entry for a path that is simply wrong.

### Do not "fix" these

They are correct for the current stage and a test asserts each one. The full table, with
the stage that changes each, is in `docs/PROJECT-STATUS.md`.

- A submitted task stays `pending` forever — no execution engine until Stage 7, and
  `make smoke` asserts `pending` on purpose.
- Every arm's own endpoint returns 501 — a convincing stub would make an unimplemented
  arm indistinguishable from a working one. Stage 8.
- `POST /arms/register` returns 503 by default — no `ORCHESTRATOR_CAPABILITY_SECRET` is
  configured, so it fails closed. Set one and it takes a capability token. Configured,
  not staged.
- Qdrant runs and is unused — Memory owns it. Stage 6.
- Six performance targets read "not measured" — there is no eval harness. Stage 10.
- Both SDKs call some routes that 404 — each is listed with its stage in
  `scripts/ci/check_sdk_parity.py`, and an entry that outlives its stage fails the check.

### Known gaps

- `services/orchestrator/pyproject.toml` declares the OpenTelemetry dependencies that
  `app/telemetry.py` imports, but the orchestrator image installs the **root**
  `pyproject.toml`, which does not. The two manifests need reconciling before that image
  can serve traced traffic.
- The five Python arms answer their own endpoint with 501. Stage 8 implements them.
- **`POST /submit` and `GET /tasks/{id}` are still open.** The one mutating registry
  endpoint now requires a capability token (Stage 5). Do not add another mutating
  endpoint without a gate, and do not accept a field that says where a service lives --
  `base_url`, `port` and `endpoint` are configuration the orchestrator owns, and a
  caller able to restate them redirects that service's traffic.
- **`RequireCapability` is deliberately NOT enforced on the six Python arms**, which
  still answer 501 naming Stage 8. Turning it on for an unimplemented endpoint would
  replace an honest 501 with a 401 and make an unbuilt arm look like a permissions
  problem. The arms adopt it in the stage that builds them.
- **`InMemoryCallCounter` is correct for one replica only.** Two replicas each keep
  their own count, so the bound degrades to `max_calls x replicas`. Use
  `RedisCallCounter` for anything scaled.

<<< MC-PROJECT-END >>>

