# Project status

**The single source of truth for where OctoLLM actually is.**

**Version**: 0.5.0 · **Updated**: 2026-09-12 · **Stages complete**: 0–6 of 12

> **If you are Claude Code starting a session, read this file first, then `CLAUDE.md`
> at the repository root.** This file is *where the project is*. `CLAUDE.md` is *how to
> work here* — commands, conventions, and the invariants you must not break.
>
> Every number below is derived from the repository, not remembered. If you change
> something that makes a number here wrong, fix it in the same change. A status file
> that drifts is worse than none, because people act on it.

---

## The one thing to understand before touching anything

This repository spent its first phase describing a system that had not been built, and
nothing in CI could contradict it. The audit that started the v1.0.0 plan found:

- **Zero git tags**, against a `CHANGELOG.md` documenting 13 releases.
- A `Version-1.2.0` badge over a repository where `/health` reported `0.1.0` and
  OpenTelemetry spans reported `0.9.0` — the same process, three different answers.
- The orchestrator never called an arm. Every task was born `pending` and stayed there,
  while the API replied "queued for processing".
- Six of the eight services in every diagram, compose file and SDK were empty
  `.gitkeep` directories whose images crash-looped.
- The reflex layer's only endpoint with business logic returned **500 on every
  request, for the entire life of the service** — with 240 tests passing throughout.
- Every test step in CI was `|| echo "No tests found yet"` **and**
  `continue-on-error: true`.

**The governing rule of the v1.0.0 plan is therefore: every claim in this repository is
either made true or deleted.** That applies to anything you write here, including this
file. Do not add a target that does not run, a document that describes an intention as a
fact, or a test that cannot fail.

The full plan lives at `~/.claude/plans/vectorized-singing-honey.md` (not in the repo).

---

## What runs today

| Component | State | Detail |
|---|---|---|
| **Reflex layer** (Rust, `:8080`) | **Implemented** | ~8,500 lines. PII detection, prompt-injection detection, Redis cache, token-bucket rate limiting. `POST /process` works. |
| **Orchestrator** (Python, `:8000`) | **Partial** | FastAPI, SQLAlchemy 2.0, reflex client with circuit breaker, arm registry, and the **sole capability-signing authority**. **It does not call any arm** — `/submit` validates, screens and persists. Tasks stay `pending` until Stage 7. |
| **Shared arm framework** (`octollm_common`) | **Implemented** | App factory, error envelope, contract models, arm roster, LLM providers, capability tokens, the Neural Ring and peer clients. Imported by all eight arms *and* the orchestrator. |
| **Planner / Retriever / Coder / Judge / Safety Guardian** (`:8001`–`:8005`) | **Scaffolded** | Serve `/health`, `/ready`, `/capabilities`, `/metrics`. Their own endpoint returns **501 naming Stage 8** — never a plausible fake. |
| **Executor arm** (Rust, `:8006`, host `:18006`) | **Stub** | 21 lines, serves `/health` only. Sandbox is Stage 9. |
| **Memory / Curator** (`:8007`) | **Implemented** | `POST /recall` and `POST /remember`, both capability-gated. Consumes `artifact` from the ring. Episodic vectors in Qdrant, semantic provenance in a dedicated `memory` Postgres schema. |
| **Red Team** (`:8008`) | **Not built** | Stage 11. Flag-gated off, outside the default compose profile. |
| **Python SDK / TypeScript SDK** | **Implemented** | 8 service clients each. Unpublished — neither name exists on PyPI or npm. |
| **PostgreSQL / Redis / Qdrant** | **Running** | All three are now read and written: Postgres by the orchestrator and Memory, Redis by the reflex cache and the Neural Ring, **Qdrant by Memory** — as of Stage 6 it is no longer a container nothing touches. |

`make up` brings all twelve services to **healthy**; `make smoke` passes, and it now round-trips an artifact through Memory.

### Test suites — all derived, all run by CI

| Suite | Tests | Floor | Notes |
|---|---|---|---|
| Rust workspace | **241** | — | `cargo test --workspace --all-features` |
| Rust, Redis-backed | **18** | 18 | `#[ignore]`d; 17 had never executed *anywhere* before Stage 0 |
| Shared framework | **210** | 210 | coverage floored at 90%; includes the Neural Ring against a real Redis |
| Orchestrator | **226** | 226 | coverage floored at 85% |
| Memory arm | **63** | 63 | coverage floored at 80%; against real Postgres, Qdrant and Redis |
| Python SDK | **28** | 28 | |
| TypeScript SDK | **28** (3 files) | 3 files | had no CI job at all before Stage 0 |
| **Total** | **814** | | |

**Every suite asserts a collection floor.** A suite that silently collects zero tests
produces exactly the same green check as one that ran them all. Raise a floor when you
add tests; **never lower one to make a red build green** — that is the bug, not the fix.

---

## Stage map

Each stage is one pull request whose exit criterion is *a green check that was not green
before*.

| Stage | Status | What it delivered / will deliver |
|---|---|---|
| **0** | ✅ merged (#34) | A CI gate that can fail. Turning mypy on surfaced 22 findings, four of them code that could not work. |
| **1** | ✅ merged (#40) | `Makefile` + `VERSION` + `version_sync.py`. 24 version sites had held six different answers at once. |
| **2** | ✅ merged (#41) | Secret scanning that actually scans. `.gitleaks.toml` had been discarding all ~170 built-in rules for months. |
| **3** | ✅ merged (#44) | **The stack comes up.** Six defects each made it unrunnable; two more were visible only by running it. |
| **4** | ✅ merged (#46) | **The shared arm framework.** Six defects, all in code that green tests already covered. |
| **5** | ✅ merged | **Neural Ring + capability tokens.** Built *before* any arm — retrofitting seven is strictly worse. |
| **6** | ✅ merged | **Memory / Curator arm.** Qdrant is real; global semantic memory exists. |
| **7** | ⬜ next | **Execution engine** (LangGraph), worker, cancellation. A task finally reaches `completed`. |
| **8** | ⬜ | The remaining six Python arms. Coder↔Judge peer loop converges. |
| **9** | ⬜ | Executor sandbox + capability enforcement. 18-test escape suite, plus a negative control proving escapes succeed unhardened. |
| **10** | ⬜ | Evaluation harness + benchmark gates. Real numbers replace every "TBD". |
| **11** | ⬜ | Red Team arm, flag-gated off. |
| **12** | ⬜ | Documentation truth pass, release pipeline, **cut v1.0.0**. |

**Stages 0–3 deliver a working, honest, releasable system on their own.** That is the
natural fallback boundary if scope has to be cut.

---

## What is new (Stage 6, merged 2026-09-12)

**Qdrant stopped being a container nothing reads.** It has been in the compose stack
since Phase 0 with nothing reading or writing it, while the architecture documents
described "Global Semantic Memory", "Local Episodic Memory" and "Data Diodes". Memory was
a layer with no owner.

| Piece | What it is |
|---|---|
| `services/arms/memory/` | The arm. `POST /recall`, `POST /remember`, and a Neural Ring consumer. |
| `memory` Postgres schema | `entities`, `relationships`, `task_history`, `action_log` — transcribed from `docs/implementation/memory-systems.md`, which has carried an implementable schema since before any of this was built. |
| Qdrant episodic store | One collection per (arm, embedding model). |
| `services/arms/memory/alembic/` | **The first migration environment in this repository.** |

### Alembic exists now, and so does a check that can fail

`alembic` has been a declared dependency since Phase 0, and four documents told people to
run `alembic upgrade head` against a project with no `alembic.ini`, no `env.py` and no
`versions/`. Tables came from `Base.metadata.create_all`.

`make migrate-check` compares the ORM against the migrated database. **It caught four
real disagreements the first time it ran** — two `DESC` indexes declared without their
ordering, and two GIN indexes written as raw SQL in the migration and so invisible to the
comparison. A schema described twice with nothing forcing agreement is the defect this
repository spent its first phase in.

The orchestrator's `public` tables still come from `create_all`. Known gap, listed below.

### The embedding-model trap, and the name that prevents it

A collection is `octollm_episodic__<arm>__<model>`. Changing embedding *dimension* fails
loudly, which is fine. Changing between two **different models of the same dimension**
does not fail at all: writes succeed, searches return results, scores look plausible, and
every one is meaningless, because cosine similarity across two embedding spaces measures
nothing. Putting the model in the name makes that a new, empty collection instead.

The dimension is **probed** from the live provider, never configured — a configured
dimension is a second place for the truth to live, and the one that goes stale.

### The data diode is enforceable now

`RecallRequest` has **no field** for the caller's clearance. It is read from a
`clearance:<level>` scope on the capability token, defaulting to `internal` when the
grant is silent. Asking for more in the body is a 422, not a quiet ignore.

That is Stage 5's roster-not-registry rule one layer out: *a caller that states its own
clearance is the same escalation as an arm that states its own peers.* Filtering happens
in the Qdrant query rather than after it, so `limit` is honoured among documents the
caller may see, and `withheld` reports the count — silently returning fewer results makes
a clearance boundary look like an empty index.

### Proven against the running stack

`make smoke` now round-trips an artifact through Memory: remember → duplicate detection →
recall, with a capability token minted against the secret the stack is actually using.
That is Stage 6's exit criterion as a green check rather than a claim.

### What Stage 6 found in Stage 5's work

Two defects, both in code that was green:

1. **`RequireCapability` checked task binding before token presence**, so a request with
   no token at all got 403 instead of 401 — collapsing the distinction Stage 5 introduced
   deliberately. Found by a Memory test asserting the 401.
2. **`scripts/mint_capability.py` wrote a structlog line to stdout**, so `$(mint...)`
   captured a log line *and* the token. Substituting that into an `Authorization` header
   produced a malformed request that uvicorn answered with a bare
   `400 Invalid HTTP request received`, naming neither the header nor the cause. The
   script's own docstring claimed stdout carried the token and nothing else.

`make sdk-parity-check` had two blind spots of its own: its TypeScript regex required a
generic type parameter, so `this.post('/x', body)` was invisible and exempt from every
assertion; and `arm_routes` knew only about `spec.endpoint`, so an arm's extra routes were
unchecked. Both are fixed, and the check now covers **9 services, 34 calls**.

### Tested against real engines

Postgres, Qdrant and Redis — not SQLite, not a hand-written double, not qdrant-client's
local mode. Every assertion worth making here is a property of the engine underneath:
`ON CONFLICT DO NOTHING` against a named constraint, a GIN index on a `tsvector`
expression, a payload filter combined with a vector search, at-least-once redelivery.
`make test-memory` **refuses to run** when they are absent rather than skipping.

### One honest limitation

With the default `FakeProvider`, `embed()` returns hash-derived unit vectors: identical
text scores 1.0, two different texts score near zero. **Recall works, is deterministic,
and is not semantic.** That keeps the stack runnable with no API keys and every test
reproducible, but a deployment reading meaning into the ordering must configure a real
embedding provider first.

Rationale and alternatives: `docs/adr/011-memory-arm-and-the-two-stores.md`.

---

## What is new (Stage 5, merged 2026-09-12)

**The arms can now talk to each other, and there is finally something that can stop
them.** Built before any arm exists, because retrofitting a ring onto seven arms that
were not designed for it is strictly worse.

Capability isolation had been 87KB of design document and **zero lines of code**, while
`docs/api/openapi/executor.yaml` required a capability token on every request and
`pyjwt[crypto]` sat in the root manifest unimported. A contract demanding a credential
nothing can mint is not a control; it is a comment.

| Module | What it is |
|---|---|
| `octollm_common/capability.py` | Mint and verify grants. HS256, `kid` from day one, ≤120s TTL, per-callee `aud`, per-task binding, and `max_calls` counted by the **callee**. |
| `octollm_common/ring.py` | Artifacts on Redis Streams, within the topology an arm declares. Consumer groups, at-least-once, explicit ack. |
| `octollm_common/peer.py` | Direct arm-to-arm HTTP for the tight loops, plus `PeerLoopContract` and the `UsageAccumulator` that makes off-graph spend visible. |
| `octollm_common/security.py` | `RequireCapability` — the callee-side FastAPI gate. Enforcement in the runtime, not in the spec. |
| `octollm_common/models/provenance.py` | The `data-flow.md` envelope verbatim, plus `trace_id`, `engagement_id`, `sensitivity` and `promoted_from`. |
| `app/capabilities.py` | The orchestrator as **sole signing authority**. |

### The one property to understand

**Authorization reads the static roster in source, never the live registry.**

`ArmRegistry` accepts `peers` from an arm's own `/capabilities` response — it must,
since its job is to report what each arm says about itself. That makes the field
arm-controlled. A compromised Coder answering its next probe with `peers: ["executor"]`
would, if the issuer trusted the registry, mint itself a path to the sandbox.

This is Stage 4's lesson applied one layer further out: *getting a principle right in
one place is not the same as applying it everywhere it holds.* A test performs the
attack — it registers the lie, confirms it landed in the registry, and asserts the token
is still refused.

### What a grant costs an attacker

A compromised Coder holding a live token reaches `{judge, retriever}`, for one task,
five calls, two minutes. It cannot refresh it, cannot present it to another arm (`aud`),
cannot use it on another task (`task_id`), and cannot exceed its budget, because the
callee counts rather than trusting the caller.

### The registration shared secret is gone

Stage 4 gated `POST /arms/register` on a shared secret and recorded it as a stopgap.
It is now a capability token: `aud=orchestrator`, `registry:write`, ≤120s, spendable
once. Verified end to end against the running stack — 401 with no token, 200 with a
minted one, **403 on replay**. `ORCHESTRATOR_ARM_REGISTRATION_TOKEN` is replaced by
`ORCHESTRATOR_CAPABILITY_SECRET`; mint with `scripts/mint_capability.py`.

### Tested against real infrastructure, not doubles

The 15 ring tests run against a **real Redis**, and CI's `test-shared` job now has a
`redis:8-alpine` service so a local skip is never a gate skip. A fake would implement
whatever `ring.py` already assumes and could not show that a group survives a restart,
that an unacknowledged message redelivers, or that `mkstream` lets a consumer start
before its producer.

The peer-client tests call a **real FastAPI callee over a real ASGI transport** that
itself enforces `RequireCapability`. That is the direct answer to the defect that
defined Stage 4: every SDK test mocked the transport, so four impossible calls stayed
green. A client tested against a mock proves only that it agrees with itself.

Forgery tests construct tokens the way an attacker would — a real issuer with the wrong
key, an `alg: none` token, a `kid` of `../../etc/passwd`, and each of the nine required
claims dropped in turn — rather than corrupting a string until the parser complains.

### Still off by design

`RequireCapability` is enforced on the orchestrator's registry endpoint and **not** on
the six Python arms, which still answer 501 naming Stage 8. Turning it on for an
unimplemented endpoint would replace an honest 501 with a 401 and make an unbuilt arm
look like a permissions problem.

Rationale and alternatives: `docs/adr/010-neural-ring-and-capability-tokens.md`.

---

## What is new (Stage 4, merged 2026-09-12)

`shared/python/octollm_common` is an installable package imported by all eight arms
**and** the orchestrator. Four seams live there, and each exists because its absence
produced a real defect:

| Module | Why it exists |
|---|---|
| `models/contracts.py` | Every arm's request/response models, defined **once**. The arms use them as FastAPI models; the orchestrator imports the same classes. A field rename is an import-time error, not a 422 in production. |
| `roster.py` | The eight arms declared once — read by each arm's `main.py`, the orchestrator's registry, and `check_port_map.py`. |
| `errors.py` | One error envelope for all nine services, `RequestValidationError` included. |
| `llm/` | The provider boundary. `create_provider()` returns `FakeProvider` unless a provider is explicitly configured. |

**No test can reach a model.** `OCTOLLM_FORCE_FAKE_LLM=1` overrides configuration
entirely, so even a test that deliberately asks for `openai` gets the fake. The
inversion is the point: forgetting means the fake, not a bill. A **missing key raises**
rather than degrading to the fake — a deployment that believes it is calling a real
model and is not would be far worse than one that refuses to start.

The arm registry is live: `GET /arms` and `POST /arms/register`.

### The six defects Stage 4 found

Every one of them sat under a green test suite.

1. **Four SDK calls could never have worked** — `POST /preprocess` against a service
   that has only ever served `/process`; `POST /tasks` against one that serves
   `/submit`; and the two SDKs used *different paths* to list arms.
2. **All sixteen SDK clients defaulted to the wrong port** — the same whole-slot shift
   already found in the OpenAPI specs. The Python planner client defaulted to the
   retriever's port; safety-guardian to Memory's.
3. **The TypeScript SDK had `health()` on no client** while the Python SDK had it on all
   eight, and `capabilities()` on no arm client.
4. **The orchestrator's error envelope contradicted its own frozen contract** — `error`
   was sometimes a string and sometimes an object, and FastAPI's `{"detail": [...]}`
   answered every 422.
5. **The block-by-policy response echoed the detected PII back to the caller**, inside
   the very response that exists to say it must not travel.
6. **`anthropic>=1.5` does not accept `temperature`** on `messages.create`. The adapter
   passed it — a 400 on every Anthropic request.

The first three survived **56 green SDK tests**, because every SDK test mocks the
transport, and *a mock is built from the same wrong belief as the client*. This is the
single most repeated lesson in this repository: 39 reflex-client tests were green over a
client that could not parse a single real response, for the same reason.

### A security review caught a real hole in this stage

`POST /arms/register` refused an unknown `arm_id` with 403 — correct reasoning, since
the orchestrator is the sole signing authority for capability tokens — while **accepting
`base_url` on a known arm**, which is the same escalation by a shorter route. An
unauthenticated caller could point `planner` at a host they controlled and every task
step would follow it, carrying task content and, from Stage 5, a capability token.

Fixed by removing `base_url`/`port`/`endpoint`/`cost_tier` from the request entirely (an
arm moves when its *configuration* moves, not when it says so) and gating the endpoint
on `ORCHESTRATOR_ARM_REGISTRATION_TOKEN`, **unset by default so it fails closed**.
(That shared secret was a recorded stopgap; Stage 5 replaced it with a capability token
and the variable no longer exists. This paragraph is kept as the history of Stage 4.)

**The generalisable lesson: getting a principle right in one place is not the same as
applying it everywhere it holds.** Enumerate every field that can redirect, elevate or
falsify — not just the obvious entry point.

---

## What is deliberately not true yet

Do not "fix" these. They are correct for the current stage, and a test asserts each one.

| Behaviour | Why | Changes in |
|---|---|---|
| A submitted task stays `pending` forever | No execution engine exists. `make smoke` **asserts** `pending` on purpose. | Stage 7 |
| Every arm's own endpoint returns **501** | A stub that answered convincingly would make an unimplemented arm indistinguishable from a working one. | Stage 8 |
| `POST /arms/register` returns **503** by default | No `ORCHESTRATOR_CAPABILITY_SECRET` is configured, so it fails closed. Set one and it takes a capability token. | configured, not staged |
| Recall ranking is not semantic | `FakeProvider` embeds by hash, so identical text matches exactly and nothing else ranks meaningfully. Configure a real embedding provider. | configured, not staged |
| Six performance targets read "not measured" | There is no eval harness yet. Whatever number comes out is what ships. | Stage 10 |
| Container images are built but not published | Gated on `ENABLE_IMAGE_PUBLISH`; there is no release to publish. | Stage 12 |
| Both SDKs call some routes that 404 | Listed with their stage in `scripts/ci/check_sdk_parity.py`; an entry that outlives its stage fails the check. | 7 and 9 |

---

## Verification

```bash
make redis                                              # required by test-shared
make verify      # everything ci-gate runs: version, diagram, gate, compose-env,
                 # port-map, sdk-parity, lint, typecheck, secrets, every suite
make test-rust-redis                                    # the one suite verify omits
make up && make smoke && make down                      # the stack, end to end
```

`make test-shared` **refuses to run** without Redis on `:6379`, because the Neural Ring
tests would otherwise skip — and a skipped suite reports exactly what a passing one
reports.

`make verify` passing and `make smoke` passing are the two claims worth making. Both
pass on `main` as of this writing.

### The gates, and what each one caught

| Gate | Found |
|---|---|
| `make gate-check` | A job can be added to `ci.yml` without being wired into `ci-gate`, making it advisory by omission. |
| `make version-check` | 24 sites holding six different versions at once. |
| `make compose-env-check` | **All 23** compose variables silently ignored by both services. |
| `make port-map-check` | Every arm's spec naming its neighbour's port; then all 16 SDK clients defaulting wrong. |
| `make sdk-parity-check` | Four SDK calls that could never have worked, and an entire capability missing from one SDK. |
| `make secrets-selftest` | A scanner that had been reporting clean while inspecting almost nothing. |
| `make smoke` | `GET /tasks/{id}` returning 500 with `DetachedInstanceError` while all 166 tests passed. |
| capability tests | That a peer client tested against a mocked transport proves only that it agrees with itself — so the callee in those tests is a real app that enforces the gate. |

Note the pattern: **each of these derives truth from the code that produces it**, rather
than comparing one written-down claim against another. That is why they work.

---

## Open decisions — these need a human

Three remain from the plan. The first blocks Stage 11; none now block Stage 5.

1. **Who signs Red Team engagement scope files, and where does that key live?**
   The scope file is the entire authorization boundary for offensive activity. Key
   custody is an operational and legal decision, not an engineering one.
   **Needed before Stage 11.**
2. **Judge `facts` / SSRF deferral.** Verifying a claim means fetching task-supplied
   URLs from inside an arm, which is an SSRF primitive. Deferred to v1.1, routed through
   the Retriever instead. Confirm the deferral.
3. **Does Memory get a dedicated `memory` Postgres schema?** Recommended separate —
   cheap now, expensive later. Stage 6.

**Resolved 2026-09-12 — the `capability-isolation.md:167` amendment**, which had blocked
Stage 5. That threat-model row asserted a compromised arm has *"no access to other arms"*;
the Neural Ring makes that false the day it ships. It now reads *"no access beyond
task-scoped, orchestrator-issued, expiring peer capabilities"*, Residual Risk unchanged at
Very Low. **Stage 5 is unblocked.**

Two smaller ones raised at Stage 4 and not yet answered:

- `GET /arms` is open while the write path is gated. The roster is arguably public
  (it is in the README, the specs and both SDKs) — but gating the read too is a
  one-line change if preferred.
- The arm-registration shared secret is a **stopgap**, chosen over a 501 because the
  endpoint genuinely works and only the authorization did not exist. Stage 5 removes it.

---

## Documents you can trust, and documents you cannot

The repository carries 341 tracked markdown files, most written ahead of the code.
Reconciling them is Stage 12. Until then:

**Authoritative:**

| File | Holds |
|---|---|
| `docs/PROJECT-STATUS.md` | this file — current state |
| `AGENTS.md` | how to work here: commands, conventions, invariants. `CLAUDE.md` and `GEMINI.md` are symlinks to it |
| `docs/api/CONTRACT.md` | the frozen API contract |
| `CHANGELOG.md` | user-visible change, under `[Unreleased]` |
| `docs/adr/` | decisions, in Nygard format |
| `README.md` | the public front door |

**Known stale — do not act on these without checking the code:**

- `docs/src/project-tracking/status.md` — "22% complete", "v1.2.0", dated 2025-11-15.
  Superseded by this file.
- `to-dos/status/` — 32 tracked files, three of them reports on the *same* sprint (0.2).
- `to-dos/MASTER-TODO.md` — the earlier seven-phase roadmap; history, not a plan.
- Anything under `docs/book/` — a committed build artifact.

If a document and the code disagree, **the code wins, and the document is the bug.**

---

## Keeping this file true

Update it at every stage boundary, and whenever one of its numbers changes. The numbers
here are derivable — do not retype them from memory:

```bash
cat VERSION
grep -E "^FLOOR_" Makefile
cargo test --workspace --all-features 2>&1 | grep -oE "^test result: ok\. [0-9]+ passed"
(cd shared/python && python -m pytest tests/ --collect-only --no-cov | tail -1)
(cd services/orchestrator && python -m pytest tests/ --collect-only --no-cov | tail -1)
```

Stage 12 adds `status-check.py`, which re-derives every number here from the repository
and exits non-zero on disagreement — at which point this file stops being a promise and
becomes a test.
