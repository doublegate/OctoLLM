# ADR-009: Performance Targets, and Why the Original Seven Were Replaced

**Status**: Accepted
**Date**: 2026-09-12
**Related**: ADR-008 (versioning), v1.0.0 plan Stages 7 and 10

## Context

`ARCHITECTURE.md` carried six performance targets with every "Measured" cell reading
**TBD**, and `README.md` carried seven more, stated as achievements. There was no
benchmark corpus, no baseline, and no harness. So the targets had never constrained
anything.

Reviewing them against the architecture and the measurements that *are* available found
three distinct problems, not one.

### 1. A target so loose it cannot detect a regression

"Reflex Layer Latency < 10ms P95" — and `benches/pii_bench.rs` opens with a comment
claiming it "validates that PII detection meets the <5ms P95 latency target".

Measured on this machine (criterion, 919-byte text):

| | |
|---|---|
| PII detection, standard pattern set | **6.3 µs** |
| Injection detection | **6.2 µs** |
| PII detection, 8.6 KB text | **47 µs** |
| Redaction (mask) | **0.12 µs** |

The detector beats its stated target by roughly **800×**. The pattern corpus could grow
fiftyfold, or someone could add a catastrophically backtracking regex, and the gate
would still pass. A target with three orders of magnitude of slack is not a gate; it is
a decoration.

The 10ms figure is not wrong for the *endpoint* — an HTTP round trip plus a Redis
lookup plausibly costs that. It was wrong as a target for the **detector**, because it
conflated the two.

### 2. A cache-hit target that describes a different product

"Reflex Cache Hit Rate > 60% (after warmup)", listed under cost efficiency.

Two things are wrong with it.

**It presumes requests repeat.** This system exists for offensive security and developer
tooling: a new target to probe, a new codebase to assess, a new diff to review. The
workload is **novel by construction**. A 60% whole-request hit rate is not an ambitious
goal for this product; it is an accurate description of a FAQ chatbot. Setting it
guarantees either permanent failure or a benchmark corpus rigged to repeat itself.

**The cache does not hold what the metric implies.** `POST /process` returns a screening
verdict — `pii_detected`, `injection_matches`, a sanitised string — and never an answer.
So the cache stores *detection results*. At a 100% hit rate, every request would still
have paid for the orchestrator and its frontier model. The metric was presented as cost
efficiency while being incapable of measuring cost.

### 3. One latency percentile across every task shape

`P50 < 2s`, `P95 < 10s`, `P99 < 30s`, applied uniformly.

A single frontier-model call takes 2-5s on its own, so `P50 < 2s` is unachievable for
any task that involves one — while `P99 < 30s` is enormously loose for a request the
reflex layer answers from cache in microseconds. The same three numbers were
simultaneously impossible and meaningless depending on which request you measured.

Two smaller inconsistencies came out of the same review: `README.md` claimed a task
success rate of "> 95%" while the charter sets the bar at **70%** of 50 synthetic
security tasks; and "PII Leakage Rate < 0.1%" cannot be evaluated without exactly the
labelled corpus that would make the honest answer *zero or not zero*.

## Decision

### Set targets against measurement, with stated headroom

The reflex-layer targets are now `P95 < 100 µs` for in-process screening of ≤1 KB
(measured ~12 µs) and `< 500 µs` at 8.6 KB (measured 47 µs). That is roughly 8-10×
headroom: enough to absorb the pattern growth Stage 8 brings, tight enough that a
pathological regex or an accidental allocation in the hot path fails the gate.

`POST /process` keeps a separate `< 10 ms P95` covering the HTTP and Redis costs the
original number was really about.

### Replace the cache-hit target with the three things it conflated

| Metric | Target | Reasoning |
|---|---|---|
| **Verdict** cache hit rate | ≥ 35% | System prompts, tool descriptions and boilerplate recur constantly even when tasks do not. This is what actually repeats. |
| **Answer** cache hit rate | ≥ 10% | Deliberately low. A high number here means the corpus does not resemble the workload. |
| **Head-bypass rate** | ≥ 25% | Requests that never invoke the planning LLM: cached answers, routine dispatch straight to an arm, and reflex rejections. This is the real cost lever. |
| Cost per task vs baseline | ≤ 50% | Charter, retained. Baseline pinned to one frontier call with the same task and context. |

Head-bypass rate is the important addition. It is the number that goes down when the
system gets more expensive, and nothing in the original set tracked it.

### Give each task shape its own latency target

| Shape | P95 |
|---|---|
| Reflex-only (cache hit or rejected) | < 50 ms |
| Single arm, one model call | < 8 s |
| Multi-arm (plan → 3+ arms → judge → synthesize) | < 45 s |
| Any shape, vs a single-shot baseline | ≤ 3× (charter) |

### Make the safety targets falsifiable

Detector quality becomes recall and false-positive rate against a labelled corpus —
PII ≥ 95% recall at ≤ 2% FP, injection ≥ 95% recall at ≤ 1% FP — replacing "> 99%
detection", which had no corpus. False positives are targeted explicitly because
over-redaction is a real cost that a recall-only target rewards ignoring.

PII leakage becomes **0 leaks in evaluated output**, not "< 0.1%". A percentage invites
tolerating a detector bug, and at the corpus sizes involved the honest answer is binary.

Sandbox containment stays binary and keeps its negative control: 18 of 18 escapes
contained, **and** a control run proving the same 18 succeed unhardened. A suite never
shown to fail is not evidence.

### Task success is 70%, not 95%

The charter's number wins. `README.md`'s "> 95%" is deleted rather than reconciled: it
appeared nowhere in the charter and nothing had ever measured it.

## Consequences

**Positive**

- Three targets are measured today rather than all seven being TBD.
- The reflex gate can now fail. At 800× slack it could not.
- Cost is tracked by a metric that responds to cost.
- Latency targets are achievable for the shapes they apply to, so missing one is a
  signal instead of a known-permanent red.

**Negative**

- More rows to maintain: twelve targets across four classes instead of seven in one
  list. Mitigated by Stage 10's harness reporting all of them from one run.
- The answer-cache target (≥ 10%) will read as unambitious to anyone who has not
  thought about the workload. That is why the reasoning is written down here.

**Neutral**

- Everything except the reflex-layer rows stays TBD until Stage 10. The difference from
  before is that each is now a falsifiable claim with a stated measurement method, and
  the plan commits to publishing whatever the harness reports.

## Alternatives considered

**Keep the targets and mark them aspirational.** Rejected: the numbers would still be
wrong, and "> 60% cache hit rate" would go on implying a workload this project does not
have. A target nobody intends to meet trains people to skim the table.

**Delete every target until Stage 10 measures something.** Rejected: the harness needs
something falsifiable to report against, and targets derived after seeing the results
are not targets.

**Keep one latency percentile for simplicity.** Rejected: it is exactly what made the
original unusable. The simplicity was purchased by making the number meaningless for
every shape but one.
