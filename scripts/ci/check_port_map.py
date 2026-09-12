#!/usr/bin/env python3
"""
One canonical port map, cross-checked against everything that states a port.

Four sources disagreed about which port each service listens on -- the Dockerfiles,
the compose files, the OpenAPI `servers:` blocks and the README -- and the
disagreements were not obvious. `docs/api/openapi/executor.yaml` documented the
executor on 8003, which is the CODER's port. The README told readers to reach the
executor at `localhost:8006`, while compose maps it to host **18006**.

The rule, settled in Stage 3: **the Dockerfile and the compose file win.** They are
what actually binds a socket; a specification is a claim about them. Everything else
is checked against CANONICAL below.

Usage:
    python scripts/ci/check_port_map.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    sys.exit("check_port_map.py requires PyYAML (pip install pyyaml)")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Service:
    """One service: the port it listens on, and where that is stated."""

    def __init__(
        self,
        *,
        container_port: int,
        host_port: int,
        compose_service: str,
        directory: str,
        openapi: str | None,
        built: bool = True,
        sdk_python: str | None = None,
        sdk_typescript: str | None = None,
    ) -> None:
        self.container_port = container_port
        # Usually the same as the container port. The executor is the exception, and
        # the exception is why this is two fields rather than one.
        self.host_port = host_port
        self.compose_service = compose_service
        self.directory = directory
        self.openapi = openapi
        self.built = built
        # The SDK module stems, where they differ between the two languages
        # (`safety_guardian.py` against `safety.ts`). None means no client exists.
        self.sdk_python = sdk_python
        self.sdk_typescript = sdk_typescript


CANONICAL: dict[str, Service] = {
    "orchestrator": Service(
        container_port=8000,
        host_port=8000,
        compose_service="orchestrator",
        directory="services/orchestrator",
        openapi="orchestrator",
        sdk_python="orchestrator",
        sdk_typescript="orchestrator",
    ),
    "reflex-layer": Service(
        container_port=8080,
        host_port=8080,
        compose_service="reflex-layer",
        directory="services/reflex-layer",
        openapi="reflex-layer",
        sdk_python="reflex",
        sdk_typescript="reflex",
    ),
    "planner": Service(
        container_port=8001,
        host_port=8001,
        compose_service="planner-arm",
        directory="services/arms/planner",
        openapi="planner",
        sdk_python="planner",
        sdk_typescript="planner",
    ),
    "retriever": Service(
        container_port=8002,
        host_port=8002,
        compose_service="retriever-arm",
        directory="services/arms/retriever",
        openapi="retriever",
        sdk_python="retriever",
        sdk_typescript="retriever",
    ),
    "coder": Service(
        container_port=8003,
        host_port=8003,
        compose_service="coder-arm",
        directory="services/arms/coder",
        openapi="coder",
        sdk_python="coder",
        sdk_typescript="coder",
    ),
    "judge": Service(
        container_port=8004,
        host_port=8004,
        compose_service="judge-arm",
        directory="services/arms/judge",
        openapi="judge",
        sdk_python="judge",
        sdk_typescript="judge",
    ),
    "safety-guardian": Service(
        container_port=8005,
        host_port=8005,
        compose_service="safety-guardian-arm",
        directory="services/arms/safety_guardian",
        openapi="safety-guardian",
        sdk_python="safety_guardian",
        sdk_typescript="safety",
    ),
    "executor": Service(
        # The one service whose host and container ports differ, so the map records
        # both. Documenting only one number is how "localhost:8006" got into the
        # README and stayed there.
        container_port=8006,
        host_port=18006,
        compose_service="executor-arm",
        directory="services/arms/executor",
        openapi="executor",
        sdk_python="executor",
        sdk_typescript="executor",
    ),
    # Not built yet; listed so the ports are reserved and the map is the whole map.
    "memory": Service(
        container_port=8007,
        host_port=8007,
        compose_service="memory-arm",
        directory="services/arms/memory",
        openapi=None,
        built=False,
    ),
    "red-team": Service(
        container_port=8008,
        host_port=8008,
        compose_service="red-team-arm",
        directory="services/arms/red_team",
        openapi=None,
        built=False,
    ),
}

COMPOSE_FILES = ("compose.yaml",)


def check_ports_are_unique() -> list[str]:
    problems = []
    for field in ("container_port", "host_port"):
        seen: dict[int, str] = {}
        for name, svc in CANONICAL.items():
            port = getattr(svc, field)
            if port in seen:
                problems.append(f"CANONICAL: {name} and {seen[port]} share {field} {port}")
            seen[port] = name
    return problems


def check_dockerfiles() -> list[str]:
    problems = []
    for name, svc in CANONICAL.items():
        if not svc.built:
            continue
        path = REPO_ROOT / svc.directory / "Dockerfile"
        if not path.is_file():
            problems.append(f"{svc.directory}/Dockerfile: missing, but {name} is marked built")
            continue
        text = path.read_text()

        exposed = {int(p) for p in re.findall(r"(?m)^EXPOSE\s+(\d+)", text)}
        if exposed and svc.container_port not in exposed:
            problems.append(
                f"{svc.directory}/Dockerfile: EXPOSE {sorted(exposed)} "
                f"but {name} is canonically {svc.container_port}"
            )

        # A HEALTHCHECK against the wrong port reports a healthy container that
        # nothing can reach, which is worse than an unhealthy one.
        for port in {int(p) for p in re.findall(r"localhost:(\d+)", text)}:
            if port != svc.container_port:
                problems.append(
                    f"{svc.directory}/Dockerfile: references localhost:{port}, "
                    f"but {name} listens on {svc.container_port}"
                )
    return problems


def check_compose(path: Path) -> list[str]:
    problems = []
    document = yaml.safe_load(path.read_text()) or {}
    services = document.get("services") or {}

    for name, svc in CANONICAL.items():
        spec = services.get(svc.compose_service)
        if spec is None:
            if svc.built and path.name == "compose.yaml":
                problems.append(f"{path.name}: {svc.compose_service} is absent but {name} is built")
            continue

        for mapping in spec.get("ports") or []:
            # rpartition, not partition: a host port written `${NAME:-8000}` contains
            # a colon of its own, so splitting at the FIRST one lands inside the
            # substitution. The container port is always the final segment.
            host, _, container = str(mapping).rpartition(":")
            # Host ports are `${NAME:-default}` so a machine with a conflict can move
            # them; the DEFAULT is what the map pins. Container ports are never
            # parameterised, because they are the contract.
            if host.startswith("${"):
                host = host.rstrip("}").rsplit(":-", 1)[-1]
            if int(container) != svc.container_port:
                problems.append(
                    f"{path.name}: {svc.compose_service} maps to container port {container}, "
                    f"but {name} listens on {svc.container_port}"
                )
            if int(host) != svc.host_port:
                problems.append(
                    f"{path.name}: {svc.compose_service} publishes host port {host}, "
                    f"but the canonical map says {svc.host_port}"
                )
    return problems


def check_openapi() -> list[str]:
    problems = []
    for name, svc in CANONICAL.items():
        if svc.openapi is None:
            continue
        path = REPO_ROOT / "docs" / "api" / "openapi" / f"{svc.openapi}.yaml"
        if not path.is_file():
            problems.append(f"docs/api/openapi/{svc.openapi}.yaml: missing")
            continue
        document = yaml.safe_load(path.read_text()) or {}
        for server in document.get("servers") or []:
            url = str(server.get("url", ""))
            for port in {int(p) for p in re.findall(r":(\d{4,5})", url)}:
                if port not in (svc.container_port, svc.host_port):
                    problems.append(
                        f"docs/api/openapi/{svc.openapi}.yaml: servers url {url!r} names port "
                        f"{port}, but {name} is {svc.container_port} "
                        f"(host {svc.host_port})"
                    )
    return problems


def check_sdks() -> list[str]:
    """
    Both SDKs' default base URLs and their stated ports.

    Every one of the sixteen was wrong: the same whole-slot shift as the OpenAPI
    specs, so the Python planner client defaulted to `localhost:8002` -- the
    retriever's -- and the safety-guardian client to 8007, which is Memory's.
    Constructing a client with no arguments therefore talked to the wrong service, or
    to nothing, and no SDK test could see it because all of them mock the transport.

    The HOST port is what belongs here: an SDK is used from a developer's machine, so
    the executor is 18006 rather than 8006.
    """
    problems = []
    sources = (
        ("sdks/python/octollm-sdk/octollm_sdk/services", "sdk_python", "py"),
        ("sdks/typescript/octollm-sdk/src/services", "sdk_typescript", "ts"),
    )

    for directory, attribute, suffix in sources:
        for name, svc in CANONICAL.items():
            stem = getattr(svc, attribute)
            if stem is None:
                continue
            path = REPO_ROOT / directory / f"{stem}.{suffix}"
            if not path.is_file():
                problems.append(f"{directory}/{stem}.{suffix}: missing, but {name} has a client")
                continue
            text = path.read_text()

            for port in {int(p) for p in re.findall(r"localhost:(\d{4,5})", text)}:
                if port != svc.host_port:
                    problems.append(
                        f"{directory}/{stem}.{suffix}: defaults to localhost:{port}, but "
                        f"{name} is published on host port {svc.host_port}"
                    )

            for port in {int(p) for p in re.findall(r"\(port (\d{4,5})\)", text)}:
                if port not in (svc.container_port, svc.host_port):
                    problems.append(
                        f"{directory}/{stem}.{suffix}: states port {port}, but {name} is "
                        f"{svc.container_port} (host {svc.host_port})"
                    )
    return problems


def main() -> int:
    problems: list[str] = []
    problems += check_ports_are_unique()
    problems += check_dockerfiles()
    problems += check_sdks()
    for name in COMPOSE_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            problems += check_compose(path)
    problems += check_openapi()

    for problem in problems:
        print(f"::error::{problem}", file=sys.stderr)

    if problems:
        print(
            f"\n{len(problems)} port disagreements. The Dockerfile and compose file are "
            "authoritative, because they are what binds; update CANONICAL only when the "
            "binding itself changes.",
            file=sys.stderr,
        )
        return 1

    built = sum(1 for s in CANONICAL.values() if s.built)
    print(f"Port map agrees across {built} built services (and {len(CANONICAL) - built} reserved):")
    for name, svc in sorted(CANONICAL.items(), key=lambda kv: kv[1].container_port):
        note = "" if svc.built else "   (reserved, not built)"
        host = f" -> host {svc.host_port}" if svc.host_port != svc.container_port else ""
        print(f"  {svc.container_port}  {name}{host}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
