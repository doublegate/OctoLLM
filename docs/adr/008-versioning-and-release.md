# ADR-008: Versioning, the VERSION File, and the Makefile as the Command Surface

**Status**: Accepted
**Date**: 2026-09-12
**Supersedes**: nothing
**Related**: ADR-005 (deployment platform), v1.0.0 plan Stages 1 and 12

## Context

Two problems, with one shape: a claim written down in many places, verified in none.

### The version

`CHANGELOG.md` documented **thirteen releases**, the README badge read `Version-1.2.0`,
and the repository had **zero git tags**. Neither `octollm-sdk` on PyPI nor `octollm-sdk`
on npm existed; no image was ever pushed. Every version number in the tree was a claim
about an artifact that was never built.

The numbers did not even agree with each other. Twenty-two places stated a version,
holding six different answers simultaneously:

| Value | Stated in |
|---|---|
| `0.1.0` | root `pyproject.toml`, orchestrator manifest, `app/__init__.py`, settings default, `HealthResponse` default, Cargo workspace |
| `0.3.0` | six OpenAPI specs |
| `0.4.0` | both SDK manifests, both SDK package attributes |
| `0.9.0` | orchestrator and reflex telemetry fallbacks — the value every emitted span would have carried |
| `1.0.0` | orchestrator OpenAPI spec |
| `1.1.0` | reflex-layer OpenAPI spec |
| `1.2.0` | README badge |

Three of those are reachable at runtime. `GET /health` reported `0.1.0` while spans
reported `0.9.0` while the README advertised `1.2.0`, for the same process.

### The commands

`README.md` instructed readers to run `make lint`, `make test` and `make help`. **There
was no Makefile.** Meanwhile each CI job carried its own copy of the commands, so the
local and CI definitions of "green" were two independent things that happened to agree.

## Decision

### 1. One `VERSION` file, propagated by a script that can fail

A single `VERSION` file at the repository root holds a plain SemVer core (no
pre-release or build metadata — several sites have their own opinions about legal
suffixes, and a value valid in one and not another is how a release breaks halfway
through). `scripts/version_sync.py` propagates it to all twenty-two sites and, with
`--check`, fails when any disagrees. CI runs `make version-check`. Two of the twenty-two
are inside `package-lock.json`, which npm does not rewrite from `package.json` on its own
-- a bump that touched only the manifest left the lockfile stating the old version.

Each site is a `(path, regex, rationale)` triple that **must match exactly once**. A
pattern matching zero or two places is a hard error, not a silent skip: a pattern that
stopped matching would report success having changed nothing, which is the same class
of defect this ADR exists to eliminate.

### 2. The current version is `0.5.0`

Not 1.2.0, and not a continuation of any number above. `0.5.0` is one step past `0.4.0`,
the highest number attached to anything resembling a real artifact (both SDKs), and it
is the first version in this repository's history that is **true in every place it
appears**. `1.0.0` is cut at Stage 12, against a tag, published packages, and attested
images.

The thirteen CHANGELOG entries are retained as a development record and relocated at
Stage 12 under a header stating plainly that no tag, image or package was ever produced
for any of them.

### 3. Tests assert against `__version__`, never a literal

Three orchestrator tests hardcoded `"0.1.0"` and broke on the first sync. They now
assert against `app.__version__`, which `version_sync.py` keeps in step. A literal there
makes every release a test edit, which teaches a suite to be edited rather than trusted.
The assertion keeps its teeth: it still fails if the payload stops reporting the package
version.

### 4. The Makefile is the command surface, and CI invokes it

Every check exists as a make target, and every CI job **runs that target** rather than
its own copy of the commands. Local and CI are then the same commands by construction,
not by discipline.

Two rules govern what may appear in it:

- **Every target works today.** A target that does not is worse than a missing one — it
  is the same failure as documentation describing a system nobody built.
- **Targets arrive with the stage that makes them true.** `up`, `smoke`, `eval` and
  `release-gate` are deliberately absent until Stages 3, 3, 10 and 12 respectively.

### 5. Collection floors live in the Makefile

The per-suite floors (150 / 28 / 3 files / 17) are defined once, as make variables, and
are therefore enforced identically locally and in CI. Raising a floor is part of adding
tests; lowering one to make a red build green is the bug, not the fix.

## Consequences

**Positive**

- A version disagreement is now a failing check rather than something a reader notices.
- `README.md`'s setup block is executable, which it had never been.
- CI cannot drift from local checks without the Makefile changing in the same commit.
- `services/orchestrator/setup.py` is deleted: it duplicated PEP 621 metadata that
  `pyproject.toml` already carried, nothing referenced it, and it declared
  `python_requires=">=3.11"` against a project that requires `>=3.14,<3.15`.

**Negative**

- Twenty-two sites is a maintenance surface. Mitigated by the exactly-once assertion, which
  converts "someone reformatted a file" from a silent wrong rewrite into a loud error
  naming the site and its rationale.
- Pinning the OpenAPI `info.version` fields to the repository version forgoes independent
  API versioning. That is a real practice, but it presumes the specs describe something:
  four mutually incompatible descriptions of these APIs exist today, and three different
  `info.version` values among them communicated nothing. They move together until
  Workstream A generates the specs from the implementations and freezes the contract; an
  amendment to this ADR is the right vehicle for splitting them again.
- `make` becomes a build dependency of CI. It is present on every GitHub-hosted runner
  and on every developer platform this project targets.

**Neutral**

- Bumping a release is `echo 1.0.0 > VERSION && make version-sync`, then committing the
  result. Stage 12 adds tag creation and the attestation chain on top of that.

## Alternatives considered

**Derive the version from the git tag (`setuptools-scm`, `cargo-release`).** Rejected for
now: it works well for Python and Rust and not at all for the README badge, the OpenAPI
specs, the telemetry fallbacks, or a `HealthResponse` default — and those were exactly
where the drift was. Worth revisiting at Stage 12 for the manifests specifically, on top
of the `VERSION` file rather than instead of it.

**Leave the numbers alone and only add the Makefile.** Rejected: `GET /health` returning a
version that matches nothing else is a live defect, not cosmetics. Anyone debugging a
deployment reads that field.

**Adopt `1.2.0` to match the README badge.** Rejected: it would ratify the highest of six
mutually contradictory claims, and would make the eventual `1.0.0` a version decrease.
