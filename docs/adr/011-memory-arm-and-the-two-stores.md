# ADR-011: The Memory Arm, Two Stores, and an Enforceable Data Diode

**Status**: Accepted
**Date**: 2026-09-12
**Supersedes**: nothing
**Related**: ADR-003 (memory architecture), ADR-010 (Neural Ring and capability tokens), v1.0.0 plan Stage 6

## Context

Memory was a layer with no owner. `docs/architecture/` describes "Global Semantic
Memory", "Local Episodic Memory" and "Data Diodes"; Qdrant has been in the compose stack
since Phase 0; and **nothing had ever read or written it**. `docs/implementation/memory-systems.md`
carried a complete, implementable SQL schema that no migration created — in a repository
where `alembic` was a declared dependency, four documents instructed people to run
`alembic upgrade head`, and there was no `alembic.ini`, no `env.py` and no `versions/`.

Memory also blocks two other things. It is the **Retriever's corpus**, so the Retriever's
design cannot be settled until storage has an owner; and Stage 7's execution graph has a
`memory_write` node with nothing to write to.

## Decision

### 1. Two stores, split by the kind of question each answers

**PostgreSQL** holds the semantic half: `entities`, `relationships`, `task_history`,
`action_log`. "Which arm produced this, under what task, and how sensitive was it" has an
exact answer, is relational, and is queried by attribute.

**Qdrant** holds the episodic half: per-arm collections of artifact embeddings. "What else
is like this" has no exact answer and is queried by similarity.

The split is not stylistic. Putting either question in the other store produces a system
that answers both badly: a vector search cannot answer an audit, and a `LIKE` query is not
a recall.

### 2. A dedicated `memory` Postgres schema

The four tables live in `memory`, not `public`. One line in the migration now; a data
move later.

The reason is blast radius. Memory ingests artifacts produced by every other arm, which
makes it the arm most exposed to content it did not write. A role scoped to
`GRANT USAGE ON SCHEMA memory` cannot read `public.tasks` however thoroughly that arm is
compromised. Sharing `public` would make the separation a migration rather than a grant.

Decided with the owner on 2026-09-12; it was open decision #3 in the plan.

### 3. Alembic, scoped to that schema, with a check that can fail

Memory owns its migrations, which follows from owning a schema. `env.py` sets
`include_object` to consider only the `memory` schema — without it, the first
`--autogenerate` against a live database would emit a migration dropping the
orchestrator's tables, and it would look entirely reasonable in review.

`make migrate-check` runs `alembic check`, comparing the ORM in `src/models.py` against
the migrated database. **It caught four real disagreements the first time it ran**: two
`DESC` indexes declared in the ORM without their ordering, and two GIN indexes written as
raw SQL in the migration and therefore invisible to the comparison. A schema described
twice with nothing forcing agreement is the defect this repository spent its first phase
in; this is the thing that forces it.

The orchestrator's `public` tables are **not** migrated by this and still come from
`Base.metadata.create_all`. That is a known gap, recorded as one.

### 4. Three fields the design document does not have

- **`action_log.artifact_id`, unique.** The document's `action_log` has no artifact
  identity and so no way to be idempotent. Ring delivery is at-least-once, so the same
  artifact arriving twice is normal operation; without this, the second delivery doubles
  the record and every count built on it is wrong. This is the `store_task_result` defect
  — an unconditional INSERT into a table with a unique key, which turned a resumed graph
  into a permanently stuck task — fixed before the traffic that would expose it.
- **`action_log.sensitivity`.** The diode is only enforceable if the label is stored.
- **`TIMESTAMPTZ`**, not the document's naive `TIMESTAMP`. A provenance record whose time
  has no zone cannot be ordered against another host's.

### 5. The collection name carries the embedding model

`octollm_episodic__<arm>__<model>`.

Per arm, because episodic memory is an arm's own experience and one shared collection
would make every recall a filtered scan over everything the system has produced.

Per **model**, because that failure has no symptom. Changing dimension fails loudly and
is therefore fine. Changing between two *different models of the same dimension* does not
fail at all: the writes succeed, the searches return results, the scores look plausible,
and every one of them is meaningless, because cosine similarity across two embedding
spaces measures nothing. A model change now produces a new, empty collection — honest,
because the old vectors genuinely cannot answer questions posed in the new space.

The dimension is **probed** from the live provider at startup, never configured. A
configured dimension is a second place for the truth to live, and the one that goes stale.

### 6. Clearance comes from the capability token, never the request

`RecallRequest` has **no field** for the caller's clearance. It is read from a
`clearance:<level>` scope on the verified token, defaulting to `internal` — the safer
level — when the grant says nothing.

This is ADR-010's roster-not-registry rule applied one layer out: *a caller that states
its own clearance is the same escalation as an arm that states its own peers.* The
request model rejects the extra field outright, so the attempt fails with 422 rather than
being quietly ignored.

Filtering happens **in the Qdrant query**, not after it. A post-filter over `limit`
results returns fewer than asked for whenever restricted material ranks highly, so the
caller sees a sparse index rather than a boundary. `withheld` is measured by a second
count and reported, because silently returning fewer results makes a clearance problem
look like an empty index.

### 7. Both HTTP routes are capability-gated

ADR-010's rule was that an arm adopts `RequireCapability` in the stage that builds it.
This is that stage. Memory holds every arm's output, so an open recall endpoint is a read
of the whole system's work.

`/recall` and `/remember` carry **separate scopes**: a single scope covering both would
make every reader an editor of the record it reads from. `/health`, `/ready`,
`/capabilities` and `/metrics` stay open — a health check that needs a credential reports
"down" whenever authorization is misconfigured, which is a different problem wearing the
same signal.

## Consequences

### Ranking is not semantic with the default provider

`FakeProvider.embed()` returns hash-derived unit vectors. Identical text scores 1.0;
two different texts score near zero. Recall works, is deterministic, and **is not
semantic**. That is the right default — it keeps the stack runnable with no API keys and
every test reproducible — but a deployment reading meaning into the ordering must
configure a real embedding provider first. Stated plainly in the OpenAPI description and
asserted in the suite, so it is a known property rather than a disappointment.

### There is no transaction across the two stores

There is no such thing across Postgres and Qdrant, and compensating deletes would produce
a system that is wrong in more interesting ways. Instead both writes are idempotent and
the semantic write goes first: if the vector write then fails, memory has lost the
ability to *find* an artifact but not the record that it existed. The reverse order would
lose the audit trail and keep a searchable copy, which is the worse half to lose. The
recovery for a partial write is to deliver the artifact again, which the ring does by
itself.

### The suite needs three real services

Postgres, Qdrant and Redis. Not SQLite, not a hand-written double, not qdrant-client's
local mode. Every assertion worth making here is a property of the engine underneath:
`ON CONFLICT DO NOTHING` against a named constraint, a GIN index on a `tsvector`
expression, a payload filter combined with a vector search, at-least-once redelivery.

`make test-memory` **refuses to run** when they are absent rather than skipping, and CI
provides all three as job services. A skipped suite reports exactly what a passing one
reports, which is the failure mode this repository keeps finding.

### Memory is the first arm that claims to be implemented

`roster.py` now has exactly one `implemented=True`, and a test asserts that list
explicitly, so Stage 8 flipping the next one has to come through it. An arm that marks
itself implemented is an arm the orchestrator will route work to; that must never happen
as a side effect.

## Alternatives considered

**Postgres with `pgvector` instead of Qdrant.** One store, one transaction, and the
partial-write problem disappears. Rejected because Qdrant is already in the stack and
already in every diagram — adding pgvector would mean either running both or removing a
service the architecture documents describe, and the transaction it buys is worth less
than idempotent writes, which are needed anyway for at-least-once delivery.

**One shared episodic collection with an `arm_id` filter.** Simpler to operate. Rejected:
every recall becomes a filtered scan over everything the system has produced, and the
per-arm boundary stops being structural.

**Deriving sensitivity in Memory rather than storing the producer's label.** Attractive
because it would centralise the policy. Rejected: a label decided by the store rather
than the producer is a label nobody can audit, and the producer is the only component
that knows what the content is.

**Letting the caller pass its clearance.** Rejected outright; see decision 6.
