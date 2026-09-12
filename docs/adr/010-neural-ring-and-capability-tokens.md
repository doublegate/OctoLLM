# ADR-010: The Neural Ring and Capability Tokens

**Status**: Accepted
**Date**: 2026-09-12
**Supersedes**: nothing
**Amends**: `docs/security/capability-isolation.md:167` (see "Consequences")
**Related**: ADR-002 (communication patterns), ADR-004 (security model), v1.0.0 plan Stage 5

## Context

The architecture documents are built on octopus neurobiology, in which most coordination
happens between arms rather than through the central brain (`Project-Overview.md:24`,
`system-overview.md:155`, `data-flow.md:387`). The design as implemented ignored that
entirely: every interaction was a star through the orchestrator.

That is two problems at once. It is the latency bottleneck the architecture exists to
avoid — a Coder/Judge validation loop pays a full orchestrator round trip per iteration —
and it is a single point whose failure stops work that did not depend on it.

`data-flow.md:399-409` already specifies direct arm-to-arm communication and imposes
three constraints on it: register intent with the orchestrator, include provenance in
all messages, respect capability boundaries. None of the three had an implementation.

The third was the worst of the three. `docs/security/capability-isolation.md` is 87KB
describing a complete JWT capability model, `docs/api/openapi/executor.yaml` has required
a capability token on every request since Phase 0, `pyjwt[crypto]` has been a declared
root dependency that nothing imported — and there were **zero lines of code**. A contract
demanding a credential that no component can mint is not a security control. It is a
comment.

## Decision

### 1. Two transports, split by what the traffic is

**Redis Streams** carry artifacts. Persistent, replayable, with consumer groups giving
at-least-once delivery and explicit acknowledgement. Chosen over pub/sub because a
consumer that was down must not silently miss work, and because the stream is the only
thing that makes "what did the arms say to each other" auditable after the fact. Redis
is already in the stack.

**Direct HTTP** carries the tight loops the documents name: Coder↔Judge above all, plus
Planner→Executor and Retriever→Coder. A validation loop that publishes an artifact and
waits for one to come back pays a broker round trip for what is conceptually a function
call, and has nowhere to record "this is iteration 3 of at most 5".

### 2. Topology is declared in the roster, and authorization reads only that

`ArmSpec` carries `publishes`, `subscribes` and `peers`. The orchestrator learns the
whole ring topology from the `GET /capabilities` call its registry was already making,
so **the ring needs no new protocol**.

The orchestrator issues a peer token only for an edge that appears in the topology. An
undeclared edge is unreachable rather than discouraged.

**Authorization reads the static roster in source, never the live registry.** This is
the load-bearing distinction. `ArmRegistry` accepts `peers` from an arm's own
`/capabilities` response — it must, since its job is to report what each arm says about
itself — which makes that field arm-controlled data. A compromised Coder answering its
next probe with `peers: ["executor"]` would, if the issuer trusted the registry, mint
itself a path to the sandbox. The registry answers "is the Judge healthy"; it never
answers "may the Coder call the Judge".

A runtime `peer.intent` event is published before a loop starts, but that is
**observation, never permission**. A synchronous "may I?" call to the orchestrator would
reintroduce exactly the bottleneck the ring exists to remove.

### 3. Capability tokens are narrow, short, and counted

HS256 JWTs saying one thing: *the orchestrator permits `sub` to call `aud`, for
`task_id`, within `scope`, at most `max_calls` times, until `exp`.*

| Property | Value | Why |
|---|---|---|
| TTL | ≤ **120s**, refused above | A peer loop is a sub-transaction inside one graph node; a longer grant outlives its purpose |
| `aud` | one arm | Stops a token for the Judge being presented to the Executor — the check the whole lateral-movement bound rests on |
| `task_id` | one task | A live token for task A on task B is lateral movement or a bug, and both want the same answer |
| `max_calls` | counted **by the callee** | A bound the caller is trusted to respect is a request, not a bound |
| `kid` | from day one | Makes key rotation, and the move to asymmetric signing, a config change rather than a protocol change |
| `algorithms` | `["HS256"]`, explicit | Letting the token's header choose is the `alg: none` forgery |

The orchestrator is the **sole signing authority**. No arm mints a token, and there is
no endpoint that issues one on request — an endpoint that mints authority for whoever
asks is an endpoint an attacker asks nicely. Operators mint administrative tokens with
`scripts/mint_capability.py`, which requires the signing secret and therefore grants
nothing to anyone who did not already hold it.

Both issuer and verifier **fail closed at construction** on a missing, short, or
placeholder secret. A service that starts with a bad secret and fails on the first real
request has already reported itself healthy.

### 4. Peer loops never span graph supersteps

A `PeerLoopContract` bounds iterations, an absolute deadline, a token budget, and
carries the capability token. It lives inside a single node. Three independently
sufficient reasons: LangGraph checkpoints at superstep boundaries, so a spanning loop
resumes into a world where half its iterations happened; the budget ledger lives in
graph state and reconciles only at boundaries; and one node is one `StepResult` is one
audit row.

Every arm response therefore carries **cumulative `usage`** covering its own spend and
its peers'. The orchestrator cannot observe a peer call — that is the point of the ring
and also the hole it opens — so without this it is not under-reporting off-graph spend,
it is structurally unable to report it.

### 5. Provenance carries four fields beyond the document

`data-flow.md:410-430` is transcribed verbatim, plus `trace_id` (a ring message is
otherwise the one hop with no place in a trace), `engagement_id` (Red Team audit
binding, Stage 11 — retrofitting it later would leave every earlier artifact unable to
answer), `sensitivity` (what makes the data diode enforceable rather than aspirational),
and `promoted_from` (memory lineage, Stage 6 — promotion without lineage is how a wrong
fact becomes permanent and unattributable).

`sensitivity` defaults to `internal`, never `public`: an artifact nobody labelled is one
nobody thought about, and the default must be the safer of the two.

## Consequences

### `capability-isolation.md:167` was false the day this shipped

That threat-model row asserted a compromised arm has *"no access to other arms"*. The
ring makes that untrue. It has been amended to *"no access beyond task-scoped,
orchestrator-issued, expiring peer capabilities"*.

The net privilege change is a **narrowing of the orchestrator's own authority, delegated
downward** — a compromised Coder reaches `{judge, retriever}`, one task, five calls, two
minutes, and nothing else, where previously the orchestrator held and exercised all of
it. But a security document that overstates its guarantees is worse than none, because
people plan against it. The amendment was raised with the owner before Stage 5 began and
approved on 2026-09-12.

### HS256 is symmetric, and that is a real limitation

Any process holding the verification secret could forge a token. Today the verifiers are
the arms, which are inside the trust boundary, and the orchestrator is the only issuer.
`kid` exists so that moving to asymmetric signing — where arms hold only a public key and
forgery requires the orchestrator's private key — is a key-map change. That move is not
scheduled; it becomes worth its cost when arms run outside one trust boundary.

### The in-memory call counter is correct only for a single replica

Two replicas of one arm each keep their own count, degrading the bound to
`max_calls × replicas`. `RedisCallCounter` is the correct implementation for a scaled
deployment and shares the Redis the ring already requires. This is documented at the
class rather than left to be discovered.

### The arm-registration shared secret is gone

Stage 4 gated `POST /arms/register` on a shared secret and recorded it as a stopgap.
It is now a capability token addressed to the orchestrator carrying `registry:write` —
narrower in three ways: it expires within 120 seconds, it cannot be presented to an arm,
and it is counted, so a captured `Authorization` header is worth at most one replay
inside a two-minute window. `ORCHESTRATOR_ARM_REGISTRATION_TOKEN` is replaced by
`ORCHESTRATOR_CAPABILITY_SECRET`.

### Enforcement is opt-in per route until Stage 8

`RequireCapability` exists and is enforced on the orchestrator's registry endpoint, but
the six Python arms still answer their own endpoints with 501 naming Stage 8. Turning
enforcement on for an endpoint that is not implemented would replace an honest 501 with
a 401 and make an unbuilt arm look like a permissions problem. The arms adopt it in the
stage that builds them — which is why the ring is built **before** the arms rather than
retrofitted onto seven of them.

## Alternatives considered

**Kafka or NATS instead of Redis Streams.** Both are better message brokers. Neither is
already in the stack, and Redis Streams provide persistence, consumer groups and replay —
the three properties actually required. Adding a broker to operate is a real cost against
no capability difference at this scale.

**Orchestrator-mediated peer calls ("may I call the Judge?").** Keeps a single
authorization point, and reintroduces the per-iteration round trip the ring exists to
remove. Rejected: the token *is* the pre-authorization, which is the entire reason
capabilities beat an ACL check here.

**Long-lived per-arm identity tokens.** Simpler to operate, and standing authority — a
stolen token is useful until it expires, against any task. Rejected in favour of grants
narrow enough that theft buys minutes against one task.

**mTLS instead of tokens.** Authenticates the *arm*, not the *grant*: it answers "is this
really the Coder" and not "may the Coder call the Judge for this task, five times". The
two are complementary, and mTLS is a deployment concern that can be added underneath this
without changing it.
