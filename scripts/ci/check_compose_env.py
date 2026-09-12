#!/usr/bin/env python3
"""
Assert that every environment variable a compose file sets is one the service reads.

This exists because none of them were. The development compose file passed the
orchestrator seventeen variables -- `DATABASE_URL`, `REDIS_URL`, `REFLEX_URL` and the
rest -- while `app/config.py` declares `env_prefix="ORCHESTRATOR_"`, so Settings looked
for `ORCHESTRATOR_DATABASE_URL` and found nothing. Every service in the stack ran on
its compiled-in defaults, and nothing anywhere said so: the container started, the
health endpoint answered, and the database URL pointed at localhost.

The reflex layer was worse. Its config source used `separator("_")`, which cannot tell
a section boundary from a word boundary, so `REFLEX_RATE_LIMIT_ENABLED` resolved to
`rate.limit.enabled` rather than `rate_limit.enabled`. Five of its twenty-four fields
were reachable by any environment variable at all.

A misspelt or unprefixed variable is silently ignored by both Pydantic Settings and the
Rust `config` crate -- by design, since neither can know which of the host's variables
are meant for it. That makes this class of defect invisible without a check like this
one.

The two schemas are read from the code rather than restated here:

  * orchestrator -- `Settings.model_fields`, imported directly.
  * reflex layer -- the `set_default("section.field", ...)` calls in `config.rs`, which
    are the authoritative list of keys the struct deserialises.

Usage:
    python scripts/ci/check_compose_env.py            # check every known compose file
    python scripts/ci/check_compose_env.py <file>...  # check specific ones
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    sys.exit("check_compose_env.py requires PyYAML (pip install pyyaml)")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ORCHESTRATOR_CONFIG = REPO_ROOT / "services" / "orchestrator" / "app" / "config.py"
REFLEX_CONFIG = REPO_ROOT / "services" / "reflex-layer" / "src" / "config.rs"

DEFAULT_COMPOSE_FILES = (
    "infrastructure/docker-compose/docker-compose.dev.yml",
    "compose.yaml",
)

# Variables that are legitimately not part of a service's own settings schema: read by
# the runtime, a library, or the container image rather than by our config object. Each
# needs a reason, because this allowlist is the only way to hide a real mistake.
UNIVERSAL_ALLOWLIST = {
    "RUST_LOG": "tracing-subscriber reads this directly",
    "RUST_BACKTRACE": "the Rust runtime reads this directly",
    "PYTHONUNBUFFERED": "CPython runtime",
    "PYTHONDONTWRITEBYTECODE": "CPython runtime",
    "PYTHONPATH": "CPython runtime",
    "TZ": "libc",
    "POSTGRES_USER": "postgres image entrypoint",
    "POSTGRES_PASSWORD": "postgres image entrypoint",
    "POSTGRES_DB": "postgres image entrypoint",
    "PGDATA": "postgres image entrypoint",
    "REDIS_ARGS": "redis image entrypoint",
    "QDRANT__SERVICE__GRPC_PORT": "qdrant reads its own config",
    "GF_SECURITY_ADMIN_USER": "grafana image",
    "GF_SECURITY_ADMIN_PASSWORD": "grafana image",
    "GF_USERS_ALLOW_SIGN_UP": "grafana image",
    "GF_INSTALL_PLUGINS": "grafana image",
}


def orchestrator_env_names() -> set[str]:
    """`ORCHESTRATOR_<FIELD>` for every field on Settings, read from the class itself."""
    sys.path.insert(0, str(REPO_ROOT / "services" / "orchestrator"))
    try:
        from app.config import Settings  # noqa: PLC0415
    except ModuleNotFoundError as exc:  # pragma: no cover
        sys.exit(
            f"cannot import the orchestrator's Settings ({exc}).\n"
            'Install it first: pip install -e "services/orchestrator[dev]"'
        )
    prefix = Settings.model_config.get("env_prefix", "")
    return {f"{prefix}{name}".upper() for name in Settings.model_fields}


def reflex_env_names() -> set[str]:
    """`REFLEX_<SECTION>__<FIELD>` for every key config.rs sets a default for."""
    text = REFLEX_CONFIG.read_text()
    keys = re.findall(r'set_default\(\s*"([a-z_]+)\.([a-z_]+)"', text)
    if not keys:  # pragma: no cover
        sys.exit(f"{REFLEX_CONFIG}: found no set_default() calls to derive the schema from")
    return {f"REFLEX_{section}__{field}".upper() for section, field in keys}


# Which schema applies to which compose service.
SCHEMAS = {
    "orchestrator": ("ORCHESTRATOR_", orchestrator_env_names),
    "reflex-layer": ("REFLEX_", reflex_env_names),
}


def check_file(path: Path) -> list[str]:
    document = yaml.safe_load(path.read_text())
    services = (document or {}).get("services") or {}
    problems: list[str] = []

    for service_name, (prefix, schema_fn) in SCHEMAS.items():
        spec = services.get(service_name)
        if spec is None:
            continue

        env = spec.get("environment") or {}
        if isinstance(env, list):  # `- KEY=value` form
            env = {item.split("=", 1)[0]: item.split("=", 1)[-1] for item in env}

        known = schema_fn()
        for key in sorted(env):
            if key in UNIVERSAL_ALLOWLIST:
                continue
            if key in known:
                continue
            if key.startswith(prefix):
                problems.append(
                    f"{path}: {service_name} sets {key}, which is prefixed correctly but "
                    f"is not a field the service reads -- it will be ignored silently"
                )
            else:
                suggestion = f"{prefix}{key}"
                hint = f" (did you mean {suggestion}?)" if suggestion in known else ""
                problems.append(
                    f"{path}: {service_name} sets {key}, which the service never reads. "
                    f"It needs the {prefix} prefix to reach the settings object{hint}"
                )

        if not problems:
            print(f"  ok  {path}: {service_name} -- {len(env)} variables, all read by the service")

    return problems


def main() -> int:
    targets = [Path(a) for a in sys.argv[1:]] or [
        REPO_ROOT / f for f in DEFAULT_COMPOSE_FILES if (REPO_ROOT / f).is_file()
    ]
    if not targets:  # pragma: no cover
        sys.exit("no compose files found to check")

    problems: list[str] = []
    for path in targets:
        if not path.is_file():
            problems.append(f"{path}: no such file")
            continue
        problems.extend(check_file(path))

    for problem in problems:
        print(f"::error::{problem}", file=sys.stderr)

    if problems:
        print(
            f"\n{len(problems)} environment variables are set but never read. "
            "A variable the service does not read is not a default -- it is a setting "
            "the operator believes they changed.",
            file=sys.stderr,
        )
        return 1

    print("\nAll compose environment variables map to a setting the service reads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
