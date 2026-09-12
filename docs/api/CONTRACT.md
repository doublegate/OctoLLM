# The OctoLLM API Contract

**Status**: Frozen as of Stage 3 of the v1.0.0 plan (2026-09-12); extended in Stage 4
with the arm surface, the registry and the shared error envelope
**Enforced by**: `make port-map-check`, `make compose-env-check`,
`make sdk-parity-check`, `services/orchestrator/tests/test_reflex_contract.py`

Four mutually incompatible descriptions of these APIs existed: the implementations,
the OpenAPI specifications, `docs/api/component-contracts.md`, and the two SDKs.
Nothing could be built on top of them until one won. This document records which one
did, and why.

## The rule: the implementation wins, and specs are generated from it

For the two services that exist — the reflex layer and the orchestrator — the running
code is the contract, and the specification is checked against it. Hand-maintained
specs have already drifted four separate times here, in ways nobody noticed for
months. For arms that do not exist yet, the hand-written spec remains the contract,
because there is nothing else; it becomes generated the moment the arm is built.

The one case where a specification is *not* authoritative even in principle is the
port map. A Dockerfile and a compose file bind sockets. A specification is a claim
about what they did.

## Ports

**The Dockerfile and the compose file are authoritative.** `scripts/ci/check_port_map.py`
holds the canonical map and checks every Dockerfile, compose file and OpenAPI
`servers:` block against it.

| Service | Container | Host | Notes |
|---|---|---|---|
| orchestrator | 8000 | 8000 | |
| planner | 8001 | 8001 | |
| retriever | 8002 | 8002 | |
| coder | 8003 | 8003 | |
| judge | 8004 | 8004 | |
| safety-guardian | 8005 | 8005 | directory renamed from `safety-guardian` to `safety_guardian` |
| executor | 8006 | **18006** | the only service whose host and container ports differ |
| memory | 8007 | 8007 | reserved; Stage 6 |
| red-team | 8008 | 8008 | reserved; Stage 11 |
| reflex-layer | 8080 | 8080 | |

Every arm's OpenAPI spec named the wrong port before this was checked, shifted a
whole slot: the planner documented 8002 (the retriever's), the retriever 8004 (the
judge's), the executor 8003 (the coder's). The README told readers to reach the
executor at `localhost:8006` when compose publishes **18006**.

## Naming

`guardian-arm` is **`safety-guardian-arm`** everywhere: the compose service, the
image, the arm id. The Python package directory is `safety_guardian`, because
`safety-guardian` is not a legal Python identifier and the Dockerfile's
`uvicorn services.arms.safety-guardian.src.main:app` could never have resolved.

## Wire format

**snake_case, everywhere, including enum values.** The reflex layer previously
serialised `ProcessStatus` with `rename_all = "lowercase"`, which flattens
`RateLimited` to `ratelimited` — a value no consumer can split back into words — and
its `PIIType`, `InjectionType` and `Severity` enums carried no rename attribute at
all, emitting Rust variant names like `"IgnorePreviousInstructions"`.

**Acronyms are pinned explicitly.** serde's `snake_case` inserts a separator before
every capital, so `SSN` becomes `s_s_n` and `IPv4` becomes `i_pv4`. Five variants
carry an explicit `#[serde(rename)]`: `ssn`, `ipv4`, `ipv6`, `itin`, `dan_variant`.

**A span, not an offset.** Detection matches carry `start` (inclusive) and `end`
(exclusive) plus `matched_text`. The orchestrator's client expected a single
`position` and a `value`, which is strictly less information than redaction needs.

**Unknown enum values are rejected, not coerced.** A contract violation must be loud.

### `POST /process` (reflex layer)

```jsonc
{
  "request_id": "uuid",
  "status": "success" | "blocked" | "rate_limited" | "error",
  "pii_detected": false,
  "pii_matches": [
    {"pii_type": "email", "start": 12, "end": 29,
     "matched_text": "alice@example.com", "confidence": 0.9}
  ],
  "injection_detected": false,
  "injection_matches": [
    {"injection_type": "ignore_previous_instructions", "severity": "critical",
     "matched_text": "ignore all previous instructions", "start": 0, "end": 32,
     "confidence": 1.0, "indicators": ["ignore", "instructions"]}
  ],
  "cache_hit": false,
  "processing_time_ms": 1.16
}
```

Golden samples of every shape live in `services/orchestrator/tests/fixtures/`,
captured from a running service by `scripts/capture_reflex_fixtures.py` — never
hand-written from the client's models, which is how the previous mismatch survived
39 passing tests.

## Task identity and status

`task_id` is a **bare UUIDv4**, which is already the Postgres primary key. Not
`task_abc123xyz789`, which appears throughout the documentation and in both SDKs'
examples and is not a format anything produces.

Status is one of `pending | processing | completed | failed | cancelled`.

> Today every task is born `pending` and stays there: nothing assigns any other
> value, because the orchestrator does not yet call an arm. The execution engine in
> Stage 7 is what makes the other four reachable. `scripts/smoke.sh` asserts
> `pending` on purpose rather than pretending otherwise.

## Errors

A single nested envelope, in **both** services, including FastAPI's 422:

```json
{"error": {"code": "not_implemented", "message": "...", "details": {},
           "request_id": "...", "timestamp": "..."}}
```

All nine services install the same handlers, from `octollm_common.errors`. FastAPI's
default `{"detail": [...]}` for validation failures was the one hole — the app
returned the nested envelope for `HTTPException` and FastAPI's own shape for a 422, so
a client had to branch on the status code to know which to parse. It is closed as of
Stage 4.

`code` is the field to branch on; the message is for a human. `details` is always
present, `{}` when empty, so a client never branches on its absence, and it **never
contains a rejected value**: a validation failure reports the field and the reason,
not the input, and a request blocked for PII reports the span rather than the text.
`request_id` is always present — echoed from `X-Request-ID` when the caller sent one,
minted otherwise.

| `code` | Status |
|---|---|
| `bad_request` | 400 |
| `blocked_by_policy` | 400 (reflex layer found PII or an injection attempt) |
| `unauthenticated` / `forbidden` | 401 / 403 |
| `not_found` / `conflict` | 404 / 409 |
| `validation_error` | 422 |
| `rate_limited` | 429 |
| `not_implemented` | 501 (an arm that Stage 8 has not built yet) |
| `unavailable` | 503 |
| `internal_error` | 500 |

## The arm surface

Every arm is built by `octollm_common.create_arm_app`, which gives all eight the same
five routes and no room to differ:

| Route | |
|---|---|
| `GET /health` | liveness while the process is up |
| `GET /ready` | readiness, stating `implemented` honestly |
| `GET /capabilities` | the arm's `ArmSpec`, which is what the registry reads |
| `GET /metrics` | Prometheus exposition |
| `POST <endpoint>` | the arm's own work — `/plan`, `/search`, `/code`, `/validate`, `/check`, `/execute` |

An arm with no implementation answers its own endpoint with **501 naming the stage
that builds it**, and its OpenAPI document still describes the request body it *will*
accept. A stub that answered convincingly would make an unimplemented arm
indistinguishable from a working one.

`GET /capabilities` also carries `publishes`, `subscribes` and `peers` — the Neural
Ring topology — so the orchestrator learns it from a call it was already making. The
orchestrator issues a peer capability token **only** for an edge named in `peers`.

## The arm registry

`GET /arms` on the orchestrator, **not** `GET /capabilities`. Both SDKs shipped this
call against an endpoint that did not exist and disagreed about the path; on an arm,
`/capabilities` means that arm's own declaration, and reusing the name here for "the
arms I know about" is the kind of near-collision that produces a wrong client later.

All eight arms are returned, including the two that are not built yet, each naming its
stage. An arm that is down reports `status: "unavailable"` rather than disappearing:
"down" and "does not exist" are different facts, and the registry is the only thing
that can tell them apart. `?refresh=true` probes each arm's `/capabilities` first; it
is off by default because this endpoint is polled.

`POST /arms/register` **updates** an arm in the roster. Three refusals, and each one
is the same principle applied at a different layer:

- **503 when no token is configured**, which is the default. The service has no
  authentication at all until Stage 5 issues capability tokens, and an unauthenticated
  caller able to restate an arm's details controls where the orchestrator sends work.
  It fails closed. `ORCHESTRATOR_ARM_REGISTRATION_TOKEN` enables it; the token is
  compared in constant time. This is a stopgap that Stage 5 removes.
- **403 for an unknown `arm_id`.** The orchestrator is the sole signing authority for
  capability tokens, so an endpoint that could add an arm to the routing table is a
  privilege escalation with extra steps.
- **422 for `base_url`, `port`, `endpoint` or `cost_tier`**, which are not accepted
  fields. A caller able to restate where an arm listens could redirect that arm's
  traffic to a host it controls — every task step routed there, carrying task content
  and, from Stage 5, a capability token. Refusing an unknown `arm_id` while accepting
  a `base_url` on a known one would have been no protection at all. An arm moves when
  its configuration moves, not when it says so.

The read path (`GET /arms`) stays open: the roster is public information — it is in the
README, the specs and both SDKs — and gating it would break health dashboards without
protecting anything.

The roster itself is `octollm_common.roster`, read by each arm's service module, by the
registry, and by `scripts/ci/check_port_map.py`. There is no second list.

## The SDKs are checked against the implementations

`make sdk-parity-check` derives what each service serves from the code that serves it
and asserts that both SDKs call the same `(method, path)` set, that every call resolves
or is listed with the stage that will build it, and that each framework arm's spec
documents exactly what it serves.

Every SDK test mocks its transport, which is why four broken calls survived 56 green
tests: a mock is built from the same wrong belief as the client. `POST /preprocess`
became `POST /process`, `POST /tasks` became `POST /submit`, and `GET /capabilities`
became `GET /arms`. Sixteen clients also defaulted to the wrong port — the same
whole-slot shift as the specs — which `make port-map-check` now covers.

Calls that are deliberately ahead of the implementation are listed in
`scripts/ci/check_sdk_parity.py` with the stage that builds them, and an entry that
outlives its stage fails the check.

## What was deleted

The `POST /{arm_id}/execute` / `ArmRequest` section of
`docs/api/component-contracts.md` conflicted with every other source — the specs,
both SDKs and the implementations — and describes an interface nothing implements.
It is the fourth contract, and it loses.

## Environment variables

Each service reads its own prefix, and a variable that does not match is **silently
ignored** by both Pydantic Settings and the Rust `config` crate:

| Service | Prefix | Section separator |
|---|---|---|
| orchestrator | `ORCHESTRATOR_` | — (flat) |
| reflex-layer | `REFLEX_` | `__` |

So `ORCHESTRATOR_DATABASE_URL`, and `REFLEX_RATE_LIMIT__FREE_TIER_RPM`. All 23
variables the compose file previously set were ignored; `make compose-env-check`
now fails the build on any that would be.
