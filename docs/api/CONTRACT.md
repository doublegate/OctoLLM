# The OctoLLM API Contract

**Status**: Frozen as of Stage 3 of the v1.0.0 plan (2026-09-12)
**Enforced by**: `make port-map-check`, `make compose-env-check`,
`services/orchestrator/tests/test_reflex_contract.py`

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

FastAPI's default `{"detail": [...]}` for validation errors is the one remaining
exception, and it is a defect rather than a design: the app already returns the
nested envelope for `HTTPException`, so the shape a client sees depends on which
kind of error occurred. Fixed alongside the shared framework in Stage 4.

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
