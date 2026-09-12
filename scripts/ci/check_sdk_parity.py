#!/usr/bin/env python3
"""
Both SDKs must describe the same API, and it must be the API that exists.

Every SDK test in this repository mocks the transport. That is normal and it is also
why these defects survived for the life of the project: the Python SDK asked the reflex
layer for `POST /preprocess` (it has only ever served `/process`), both SDKs posted
tasks to `POST /tasks` (the orchestrator serves `/submit`, and `/tasks/{id}` is the read
path), and the two disagreed about how to list arms -- TypeScript asked `/arms`, Python
asked `/capabilities`. Fifty-six green tests, four broken calls.

A mocked test cannot catch this, because the mock is built from the same wrong belief as
the client. So this check does not mock anything. It derives what each service **serves**
from the code that serves it:

  * the orchestrator, by importing its FastAPI app and reading its route table;
  * the arms, from `octollm_common.roster` plus the five paths `create_arm_app` gives
    every arm;
  * the reflex layer and the executor, by parsing the `.route(...)` calls in their
    `main.rs`.

and then asserts four things:

  1. Both SDKs call the same `(method, path)` set. A capability in one and not the
     other is a client that silently cannot do what its sibling can.
  2. Every call either resolves to a served route, or appears in PENDING below with
     the stage that will build it. A path that is neither is a 404 waiting to happen.
  3. Each framework arm's OpenAPI spec documents exactly the routes it serves --
     no more, no fewer.
  4. Nothing in PENDING is actually served. An entry that outlives its stage turns
     this file into the stale documentation it exists to prevent.

Usage:
    python scripts/ci/check_sdk_parity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))
sys.path.insert(0, str(REPO_ROOT / "services" / "orchestrator"))

Call = tuple[str, str]  # (METHOD, path)

#: Which SDK module talks to which service. The two SDKs do not agree on file names --
#: `safety_guardian.py` against `safety.ts` -- so the mapping is explicit rather than
#: inferred from the filename.
SDK_MODULES: dict[str, tuple[str, str]] = {
    # service id: (python module stem, typescript module stem)
    "orchestrator": ("orchestrator", "orchestrator"),
    "reflex-layer": ("reflex", "reflex"),
    "planner": ("planner", "planner"),
    "retriever": ("retriever", "retriever"),
    "coder": ("coder", "coder"),
    "judge": ("judge", "judge"),
    "safety-guardian": ("safety_guardian", "safety"),
    "executor": ("executor", "executor"),
}

#: Calls both SDKs make against something no service serves yet, each with the stage
#: that builds it. Every entry here is a documented 404: the SDK method exists, and
#: calling it today fails. They are listed rather than deleted because the stage that
#: builds each one is scheduled, and a deleted method would have to be reinvented --
#: but an entry that outlives its stage fails this check, so the list cannot rot.
PENDING: dict[tuple[str, str, str], str] = {
    ("orchestrator", "DELETE", "/tasks/{id}"): "Stage 7 (execution engine + cancellation)",
    ("reflex-layer", "GET", "/cache/stats"): "Stage 7 (the response cache the arc needs)",
    ("reflex-layer", "POST", "/cache/clear"): "Stage 7 (the response cache the arc needs)",
    ("executor", "POST", "/execute"): "Stage 9 (the hardened sandbox)",
    ("executor", "GET", "/capabilities"): "Stage 9 (the executor is still a Rust hello-world)",
    ("executor", "GET", "/sandbox/{id}/status"): "Stage 9 (the hardened sandbox)",
}

#: Every arm served by `create_arm_app`, in addition to its own endpoint.
FRAMEWORK_PATHS: tuple[Call, ...] = (
    ("GET", "/health"),
    ("GET", "/ready"),
    ("GET", "/capabilities"),
    ("GET", "/metrics"),
)


def normalise(path: str) -> str:
    """
    Collapse every way of writing a path parameter to `{id}`.

    A Python f-string, a TypeScript template literal and a FastAPI route declare the
    same parameter three different ways; comparing them literally would report a
    difference on every parameterised path and hide the real ones.
    """
    path = re.sub(r"\$\{[^}]+\}", "{id}", path)  # TypeScript `${taskId}`
    path = re.sub(r"\{[^}]+\}", "{id}", path)  # f-string and FastAPI
    return path.rstrip("/") or "/"


# ---------------------------------------------------------------------------
# What the SDKs call
# ---------------------------------------------------------------------------

_PY_CALL = re.compile(
    r"""self\.(get|post|put|delete|patch)\(\s*f?["']([^"']+)["']""",
    re.VERBOSE,
)
_PY_PLAIN = re.compile(r"""_make_plain_text_request\(\s*["'](\w+)["'],\s*f?["']([^"']+)["']""")
# `[^(]*` rather than `[^>]*` for the type parameter: a nested generic such as
# `Record<string, unknown>` contains a `>` of its own, and stopping at the first one
# silently skipped every call that used one. A type parameter never contains `(`.
_TS_CALL = re.compile(r"""this\.(get|post|put|delete|patch)<[^(]*?>\(\s*[`'"]([^`'"]+)[`'"]""")


def python_sdk_calls(stem: str) -> set[Call]:
    source = (REPO_ROOT / "sdks/python/octollm-sdk/octollm_sdk/services" / f"{stem}.py").read_text()
    calls = {(method.upper(), normalise(path)) for method, path in _PY_CALL.findall(source)}
    calls |= {(method.upper(), normalise(path)) for method, path in _PY_PLAIN.findall(source)}
    return calls


def typescript_sdk_calls(stem: str) -> set[Call]:
    source = (REPO_ROOT / "sdks/typescript/octollm-sdk/src/services" / f"{stem}.ts").read_text()
    calls = {(method.upper(), normalise(path)) for method, path in _TS_CALL.findall(source)}
    # Plus whatever `BaseClient` itself calls -- `health()` lives there, because
    # `GET /health` is the one route all eight services have in common. Reading only
    # the service files would report it missing from every client that inherits it.
    return calls | _typescript_base_calls()


def _typescript_base_calls() -> set[Call]:
    source = (REPO_ROOT / "sdks/typescript/octollm-sdk/src/client.ts").read_text()
    # Only the public convenience methods; the `protected` verb helpers below them
    # take `path` as a parameter and match nothing.
    return {(method.upper(), normalise(path)) for method, path in _TS_CALL.findall(source)}


# ---------------------------------------------------------------------------
# What the services serve
# ---------------------------------------------------------------------------


def orchestrator_routes() -> set[Call]:
    """Read the live route table. Not a list of paths someone wrote down."""
    from app.main import app  # noqa: PLC0415 - importing is the point

    routes: set[Call] = set()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.add((method, normalise(route.path)))
    return routes


def arm_routes(arm_id: str) -> set[Call]:
    from octollm_common.roster import SPECS  # noqa: PLC0415

    spec = SPECS[arm_id]
    return {*FRAMEWORK_PATHS, ("POST", normalise(spec.endpoint))}


_RUST_ROUTE = re.compile(r"""\.route\(\s*"([^"]+)"\s*,\s*(get|post|put|delete|patch)\(""")


def rust_routes(main_rs: Path) -> set[Call]:
    return {
        (method.upper(), normalise(path))
        for path, method in _RUST_ROUTE.findall(main_rs.read_text())
    }


def served() -> dict[str, set[Call]]:
    """What each service actually answers, derived from the code that answers it."""
    routes = {
        "orchestrator": orchestrator_routes(),
        "reflex-layer": rust_routes(REPO_ROOT / "services/reflex-layer/src/main.rs"),
        "executor": rust_routes(REPO_ROOT / "services/arms/executor/src/main.rs"),
    }
    for arm_id in ("planner", "retriever", "coder", "judge", "safety-guardian"):
        routes[arm_id] = arm_routes(arm_id)
    return routes


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------


def check_service(service: str, available: set[Call]) -> list[str]:
    """Assertions 1 and 2, for one service."""
    python_stem, typescript_stem = SDK_MODULES[service]
    python_calls = python_sdk_calls(python_stem)
    typescript_calls = typescript_sdk_calls(typescript_stem)
    failures: list[str] = []

    # 1. The two SDKs must describe the same API.
    for method, path in sorted(python_calls - typescript_calls):
        failures.append(
            f"{service}: the Python SDK calls {method} {path} and the TypeScript SDK "
            f"does not. A capability in one client and not the other is a silent "
            f"difference between two things that claim to be the same API."
        )
    for method, path in sorted(typescript_calls - python_calls):
        failures.append(
            f"{service}: the TypeScript SDK calls {method} {path} and the Python SDK does not."
        )

    # 2. Every call resolves, or is a listed, dated 404.
    for method, path in sorted(python_calls | typescript_calls):
        if (method, path) in available or (service, method, path) in PENDING:
            continue
        failures.append(
            f"{service}: the SDKs call {method} {path}, which no route serves and which "
            f"is not listed in PENDING. Either fix the path, build the route, or list it "
            f"with the stage that will."
        )
    return failures


#: Arms whose whole route set is decided by `create_arm_app`, so the spec can be
#: checked against it exactly. The executor is Rust and the other two services have
#: hand-written specs describing more than they serve, which PENDING already covers.
FRAMEWORK_ARMS = ("planner", "retriever", "coder", "judge", "safety-guardian")


def check_specs_match_routes(routes: dict[str, set[Call]]) -> list[str]:
    """
    An arm's OpenAPI spec must describe exactly the paths its framework serves.

    Every one of these specs named its neighbour's port before Stage 3 -- the planner
    documented 8002, which is the retriever's. A spec nobody checks is a document that
    drifts silently, and these five are the case where drift is preventable outright:
    `create_arm_app` decides the whole route set, so the spec has no room to be
    creative.
    """
    try:
        import yaml  # noqa: PLC0415
    except ModuleNotFoundError:  # pragma: no cover
        return ["check_sdk_parity.py needs PyYAML to check the OpenAPI specs"]

    failures = []
    for arm_id in FRAMEWORK_ARMS:
        path = REPO_ROOT / "docs/api/openapi" / f"{arm_id}.yaml"
        document = yaml.safe_load(path.read_text()) or {}
        documented = {normalise(p) for p in document.get("paths", {})}
        served_paths = {p for _, p in routes[arm_id]}

        for missing in sorted(served_paths - documented):
            failures.append(
                f"{arm_id}: the arm serves {missing} and docs/api/openapi/{arm_id}.yaml "
                f"does not document it."
            )
        for extra in sorted(documented - served_paths):
            failures.append(
                f"{arm_id}: docs/api/openapi/{arm_id}.yaml documents {extra}, which the "
                f"arm does not serve. A spec that describes a route nobody wrote is how "
                f"this repository came to have four incompatible descriptions of one API."
            )
    return failures


def check_pending_is_current(routes: dict[str, set[Call]]) -> list[str]:
    """Assertion 3: an exemption that outlives its stage is stale documentation."""
    return [
        f"{service}: PENDING still lists {method} {path} against {stage}, but the service "
        f"serves it now. Remove the entry -- a stale exemption is how this file becomes "
        f"the documentation it exists to replace."
        for (service, method, path), stage in sorted(PENDING.items())
        if (method, path) in routes.get(service, set())
    ]


def main() -> int:
    routes = served()
    failures: list[str] = []
    for service in SDK_MODULES:
        failures += check_service(service, routes.get(service, set()))
    failures += check_specs_match_routes(routes)
    failures += check_pending_is_current(routes)

    if failures:
        print(f"SDK parity: {len(failures)} problem(s)\n")
        for failure in failures:
            print(f"::error::{failure}")
        return 1

    total = sum(
        len(python_sdk_calls(py) | typescript_sdk_calls(ts)) for py, ts in SDK_MODULES.values()
    )
    print(f"SDK parity: OK -- {total} calls across {len(SDK_MODULES)} services agree.")
    print(f"{len(PENDING)} call(s) documented as not yet served:")
    for (service, method, path), stage in sorted(PENDING.items()):
        print(f"  {service:<14} {method:<6} {path:<24} {stage}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
