#!/usr/bin/env python3
"""
Mint a capability token from the command line.

There is deliberately **no endpoint** that issues capability tokens on request. An
endpoint that mints authority for anyone who asks is an endpoint an attacker asks
nicely; peer tokens are minted per task step by the execution engine, inside the
orchestrator, and never in response to a request from an arm.

That leaves one legitimate need this script covers: an operator performing an
administrative action, such as `POST /arms/register`. It reads the same secret the
orchestrator signs with, so it can only be run by someone who already holds that
secret -- which is to say, by someone who could already sign anything.

Usage:

    export ORCHESTRATOR_CAPABILITY_SECRET=$(openssl rand -hex 32)
    python scripts/mint_capability.py --scope registry:write

    curl -X POST localhost:8000/arms/register \\
      -H "Authorization: Bearer $(python scripts/mint_capability.py --scope registry:write)" \\
      -H 'content-type: application/json' \\
      -d '{"arm_id": "planner", "implemented": true}'

The token is printed to stdout and nothing else is, so it substitutes directly into a
command. Diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))
sys.path.insert(0, str(REPO_ROOT / "services" / "orchestrator"))

import structlog  # noqa: E402

# structlog writes to STDOUT by default, and `issue_peer_token` logs `capability_issued`
# on every mint. That made this script's stdout a log line followed by the token, so
# `$(mint_capability.py ...)` captured both -- and substituting that into an
# Authorization header produced a malformed request that uvicorn answered with a bare
# `400 Invalid HTTP request received`, naming neither the header nor the cause.
#
# Diagnostics go to stderr so that the contract this file's docstring states is true:
# stdout carries the token and nothing else.
structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))

from app.capabilities import REGISTRY_WRITE_SCOPE, RingAuthority, UndeclaredEdge  # noqa: E402
from octollm_common.capability import CapabilityConfigError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mint an OctoLLM capability token.",
        epilog="The secret comes from ORCHESTRATOR_CAPABILITY_SECRET.",
    )
    parser.add_argument(
        "--scope",
        action="append",
        help=(
            "Scope to grant; repeatable. Defaults to "
            f"{REGISTRY_WRITE_SCOPE} for an admin token, and to the callee's own "
            "endpoint scope for a peer token. A `clearance:<level>` scope grants a "
            "data-diode clearance, which is how the Memory arm learns what a caller "
            "may see -- it is never read from the request."
        ),
    )
    parser.add_argument(
        "--subject",
        default=os.environ.get("USER", "operator"),
        help="Who the token is for; recorded as `sub` in the audit trail",
    )
    parser.add_argument("--ttl", type=int, default=60, help="Lifetime in seconds (max 120)")
    parser.add_argument(
        "--max-calls", type=int, default=1, help="How many times it may be spent (default: 1)"
    )
    parser.add_argument("--kid", default=os.environ.get("ORCHESTRATOR_CAPABILITY_KID", "k1"))

    peer = parser.add_argument_group("peer token (instead of an admin token)")
    peer.add_argument("--caller", help="Calling arm_id")
    peer.add_argument("--callee", help="Called arm_id")
    peer.add_argument("--task-id", help="Task the grant covers")

    args = parser.parse_args()

    secret = os.environ.get("ORCHESTRATOR_CAPABILITY_SECRET")
    if not secret:
        print(
            "ORCHESTRATOR_CAPABILITY_SECRET is not set. Generate one with:\n"
            "  export ORCHESTRATOR_CAPABILITY_SECRET=$(openssl rand -hex 32)",
            file=sys.stderr,
        )
        return 2

    try:
        authority = RingAuthority(secret=secret, kid=args.kid)
    except CapabilityConfigError as exc:
        print(f"Refusing to mint: {exc}", file=sys.stderr)
        return 2

    try:
        if args.caller or args.callee:
            if not (args.caller and args.callee and args.task_id):
                print(
                    "A peer token needs --caller, --callee and --task-id together.",
                    file=sys.stderr,
                )
                return 2
            token = authority.issue_peer_token(
                caller=args.caller,
                callee=args.callee,
                task_id=args.task_id,
                max_calls=args.max_calls,
                ttl_seconds=args.ttl,
                scope=args.scope,
            )
        else:
            token = authority.issue_admin_token(
                subject=args.subject,
                scope=(args.scope or [REGISTRY_WRITE_SCOPE])[0],
                max_calls=args.max_calls,
                ttl_seconds=args.ttl,
            )
    except UndeclaredEdge as exc:
        print(f"Refusing to mint: {exc}", file=sys.stderr)
        return 3
    except (CapabilityConfigError, ValueError) as exc:
        print(f"Refusing to mint: {exc}", file=sys.stderr)
        return 2

    print(f"expires in {args.ttl}s, spendable {args.max_calls}x", file=sys.stderr)
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
