"""
The orchestrator's capability-signing authority.

The orchestrator is the **sole** signing authority for the Neural Ring. No arm mints a
token, which is the reason `POST /arms/register` refuses to introduce an arm: an arm
the orchestrator can be told about is an arm it can be told to trust.

## Authorization reads the static roster, never the live registry

This is the single most important line in this module, and it is the direct
application of the lesson Stage 4's security review produced -- *getting a principle
right in one place is not the same as applying it everywhere it holds.*

`ArmRegistry` refreshes itself by calling each arm's `GET /capabilities`, and it
accepts `peers` from that response. It has to: the registry's job is to report what
each arm says about itself. But that makes `registry.get(arm).peers` **arm-controlled
data**. An arm that has been compromised could answer its next `/capabilities` probe
with `peers: ["executor", "red-team"]` and, if the issuer trusted the registry, mint
itself a path to the sandbox.

So the issuer reads `octollm_common.roster.SPECS` -- the static declaration in source,
reviewed in a pull request, identical in every replica and unreachable from the
network. The registry remains the right place to ask *"is the Judge healthy"*; it is
never the place to ask *"may the Coder call the Judge"*.

## What a token costs to obtain

Nothing, from inside the orchestrator. That is deliberate: peer tokens are minted per
task step by the execution engine (Stage 7), not requested by arms. There is no
"please issue me a capability" endpoint, because an endpoint that mints authority on
request is an endpoint an attacker asks nicely.
"""

from __future__ import annotations

import structlog
from octollm_common.capability import (
    MAX_TTL_SECONDS,
    CapabilityIssuer,
    CapabilityVerifier,
    InMemoryCallCounter,
    PeerConstraints,
)
from octollm_common.capability import (
    CallCounter as CallCounter,
)
from octollm_common.roster import SPECS

logger = structlog.get_logger(__name__)

__all__ = [
    "ORCHESTRATOR_AUDIENCE",
    "REGISTRY_WRITE_SCOPE",
    "RingAuthority",
    "UndeclaredEdge",
    "scope_for",
]

#: The orchestrator's own audience id, for tokens presented *to* it.
ORCHESTRATOR_AUDIENCE = "orchestrator"

#: The scope `POST /arms/register` requires.
REGISTRY_WRITE_SCOPE = "registry:write"


class UndeclaredEdge(PermissionError):
    """
    A token was requested for a peer edge the roster does not declare.

    `PermissionError` rather than `ValueError`: this is a refusal, and a caller that
    catches broad `ValueError` around plan construction must not swallow it.
    """


def scope_for(callee: str) -> str:
    """
    The scope string for calling one arm's own endpoint.

    Derived from the roster's `endpoint` so that the scope on a token and the path it
    authorizes cannot drift: `/validate` becomes `call:validate`. A hand-written scope
    table would be a fifth place the API surface is written down.
    """
    spec = SPECS[callee]
    return f"call:{spec.endpoint.lstrip('/')}"


class RingAuthority:
    """
    Mints peer capability tokens, and verifies tokens presented to the orchestrator.

    Args:
        secret: The signing secret. Validated at construction -- see
            `octollm_common.capability.validate_secret` -- so a deployment with a
            placeholder value fails to start rather than issuing forgeable grants.
        kid: Active key id.
        verification_keys: `kid` -> secret for tokens presented *to* the orchestrator.
            Defaults to the signing key alone; a rotation adds the retiring key here
            until it expires out.
        counter: Where `max_calls` is enforced for tokens the orchestrator verifies.
        default_ttl_seconds: Applied when a caller does not ask for one.
    """

    def __init__(
        self,
        *,
        secret: str,
        kid: str = "k1",
        verification_keys: dict[str, str] | None = None,
        counter: CallCounter | None = None,
        default_ttl_seconds: int = 60,
    ) -> None:
        self._issuer = CapabilityIssuer(secret, kid=kid)
        self._default_ttl = min(default_ttl_seconds, MAX_TTL_SECONDS)
        self._verifier = CapabilityVerifier(
            verification_keys or {kid: secret},
            audience=ORCHESTRATOR_AUDIENCE,
            counter=counter or InMemoryCallCounter(),
        )

    @property
    def verifier(self) -> CapabilityVerifier:
        """For routes on the orchestrator that themselves require a capability."""
        return self._verifier

    @staticmethod
    def declared_edge(caller: str, callee: str) -> bool:
        """
        Whether the roster declares `caller -> callee`.

        Reads the static roster. See the module docstring for why this must never be
        the live registry.
        """
        spec = SPECS.get(caller)
        if spec is None or callee not in SPECS:
            return False
        return callee in spec.peers

    def issue_peer_token(
        self,
        *,
        caller: str,
        callee: str,
        task_id: str,
        max_calls: int = 5,
        max_tokens: int | None = None,
        ttl_seconds: int | None = None,
        scope: str | list[str] | None = None,
    ) -> str:
        """
        Mint a grant for one declared edge, one task, and a bounded number of calls.

        Raises:
            UndeclaredEdge: the roster does not declare this edge, or either arm is
                unknown. An undeclared edge is unreachable rather than merely
                discouraged, and this is where that is true.
        """
        if not self.declared_edge(caller, callee):
            declared = sorted(SPECS[caller].peers) if caller in SPECS else []
            logger.warning(
                "capability_refused_undeclared_edge",
                caller=caller,
                callee=callee,
                declared_peers=declared,
                task_id=task_id,
            )
            raise UndeclaredEdge(
                f"The roster does not declare {caller!r} -> {callee!r}. "
                f"{caller!r} may call {declared}. Add the edge to "
                "octollm_common.roster if it is intended; it is reviewed there."
            )

        if scope is None:
            scopes = [scope_for(callee)]
        elif isinstance(scope, str):
            scopes = [scope]
        else:
            scopes = list(scope)

        token = self._issuer.issue(
            caller=caller,
            callee=callee,
            task_id=task_id,
            scope=scopes,
            constraints=PeerConstraints(max_calls=max_calls, max_tokens=max_tokens),
            ttl_seconds=ttl_seconds or self._default_ttl,
        )
        logger.info(
            "capability_issued",
            caller=caller,
            callee=callee,
            task_id=task_id,
            max_calls=max_calls,
            ttl_seconds=ttl_seconds or self._default_ttl,
        )
        return token

    def issue_admin_token(
        self,
        *,
        subject: str,
        scope: str,
        task_id: str = "admin",
        max_calls: int = 1,
        ttl_seconds: int | None = None,
    ) -> str:
        """
        Mint a token addressed to the orchestrator itself.

        Used for operator actions such as `POST /arms/register`. `aud` is the
        orchestrator, so one of these cannot be presented to an arm -- the audience
        check that stops a Judge token reaching the Executor stops this too.

        `max_calls` defaults to **1**: an administrative action is a single event, and
        a token that can be replayed four more times is four more chances for it to be
        replayed by somebody else.
        """
        return self._issuer.issue(
            caller=subject,
            callee=ORCHESTRATOR_AUDIENCE,
            task_id=task_id,
            scope=[scope],
            constraints=PeerConstraints(max_calls=max_calls),
            ttl_seconds=ttl_seconds or self._default_ttl,
        )
