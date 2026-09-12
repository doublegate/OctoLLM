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
    ) -> None:
        self.container_port = container_port
        # Usually the same as the container port. The executor is the exception, and
        # the exception is why this is two fields rather than one.
        self.host_port = host_port
        self.compose_service = compose_service
        self.directory = directory
        self.openapi = openapi
        self.built = built


CANONICAL: dict[str, Service] = {
    "orchestrator": Service(
        container_port=8000,
        host_port=8000,
        compose_service="orchestrator",
        directory="services/orchestrator",
        openapi="orchestrator",
    ),
    "reflex-layer": Service(
        container_port=8080,
        host_port=8080,
        compose_service="reflex-layer",
        directory="services/reflex-layer",
        openapi="reflex-layer",
    ),
    "planner": Service(
        container_port=8001,
        host_port=8001,
        compose_service="planner-arm",
        directory="services/arms/planner",
        openapi="planner",
    ),
    "retriever": Service(
        container_port=8002,
        host_port=8002,
        compose_service="retriever-arm",
        directory="services/arms/retriever",
        openapi="retriever",
    ),
    "coder": Service(
        container_port=8003,
        host_port=8003,
        compose_service="coder-arm",
        directory="services/arms/coder",
        openapi="coder",
    ),
    "judge": Service(
        container_port=8004,
        host_port=8004,
        compose_service="judge-arm",
        directory="services/arms/judge",
        openapi="judge",
    ),
    "safety-guardian": Service(
        container_port=8005,
        host_port=8005,
        compose_service="safety-guardian-arm",
        directory="services/arms/safety_guardian",
        openapi="safety-guardian",
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


def main() -> int:
    problems: list[str] = []
    problems += check_ports_are_unique()
    problems += check_dockerfiles()
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
