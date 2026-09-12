"""
`RequireCapability`: the callee-side enforcement point.

Everything else in the capability design is preparation for this. The issuer narrows,
the token carries the narrowing, the client presents it -- and none of that is a
security control until something on the receiving end refuses a request that does not
carry a valid one.

## Enforcement is in the runtime, not in the prompt or the contract

`docs/api/openapi/executor.yaml` has required a capability token on every request since
Phase 0, and for that whole time any caller could omit it, because a spec is a
description. This dependency is the difference.

## What the caller is told

A denied request gets a generic message and the standard error envelope. The specific
`reason` -- expired, wrong audience, budget exhausted, bad signature -- is logged and
never returned. Distinguishing "your signature is wrong" from "your token expired
four seconds ago" tells a forger which half of the problem to work on.

The status code does distinguish two cases, because they mean different things to a
well-behaved client:

- **401** when no token was presented at all. The client should obtain one.
- **403** when a token was presented and is not good enough. Retrying with the same
  token will not help, and a client that treats this as "refresh and retry" will spin.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from fastapi import HTTPException, Request, status

from .capability import (
    CapabilityClaims,
    CapabilityConfigError,
    CapabilityDenied,
    CapabilityVerifier,
)
from .errors import error_body

logger = structlog.get_logger(__name__)

__all__ = ["CapabilityPolicy", "RequireCapability", "bearer_token", "clearance_from"]

#: Scope prefix granting a data-diode clearance, e.g. `memory:clearance:confidential`.
#: Encoded in the scope list rather than as a new claim so that clearance travels
#: through the existing token format -- and, more importantly, so it is something the
#: orchestrator grants rather than something a caller states about itself.
CLEARANCE_PREFIX = "clearance:"


def clearance_from(claims: CapabilityClaims, default: str = "internal") -> str:
    """
    Read the caller's data-diode clearance out of a verified grant.

    Returns `default` -- the *safer* level -- when the token grants none. A token that
    says nothing about clearance must not thereby receive the highest one, and the
    request model deliberately has no field a caller could use to assert it.

    The highest granted level wins when several are present, which only happens if an
    issuer mints a redundant token; it is resolved rather than treated as an error
    because refusing a *wider* grant at the callee would be a confusing failure.
    """
    from .models.provenance import Sensitivity

    granted = [
        scope.removeprefix(CLEARANCE_PREFIX)
        for scope in claims.scope
        if scope.startswith(CLEARANCE_PREFIX)
    ]
    levels = [level for level in granted if level in {s.value for s in Sensitivity}]
    if not levels:
        return default
    order = [s.value for s in Sensitivity]
    return max(levels, key=order.index)


def bearer_token(request: Request) -> str:
    """
    Pull the bearer token out of an Authorization header.

    Returns an empty string when absent or when the scheme is not `Bearer`, which the
    verifier turns into a `missing_token` denial. An unknown scheme is treated as
    absent rather than as an error: a client sending Basic auth has not presented a
    capability, whatever else it has done.
    """
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


class CapabilityPolicy:
    """
    What one protected route requires.

    Args:
        verifier: The arm's verifier. One per service, shared by every route.
        scope: The action this route represents, e.g. `"call:validate"`. A route with
            no scope accepts any valid token for this audience, which is almost always
            too broad -- it is permitted so that `RequireCapability` can be used for a
            pure "is this one of ours" check, and it should be rare.
        bind_task: When true, a `X-Task-Id` header must be present and must match the
            token's `task_id`. This is what stops a live token for one task being
            replayed against another.
    """

    def __init__(
        self,
        verifier: CapabilityVerifier | None = None,
        *,
        scope: str | None = None,
        bind_task: bool = True,
        verifier_factory: Callable[[], CapabilityVerifier] | None = None,
    ) -> None:
        if (verifier is None) == (verifier_factory is None):
            raise ValueError("pass exactly one of verifier or verifier_factory")
        self._verifier = verifier
        self._factory = verifier_factory
        self.scope = scope
        self.bind_task = bind_task

    @property
    def verifier(self) -> CapabilityVerifier:
        """
        The verifier, built on first use when this policy was given a factory.

        Deferred construction matters for an arm. A verifier raises
        `CapabilityConfigError` when no signing secret is configured, and building one
        at import time would stop an unconfigured container from serving `/health` --
        turning "authorization is not set up" into "this service is down", which are
        different problems with different fixes. Deferring it means the arm starts,
        reports itself honestly, and refuses the gated routes with 503.
        """
        if self._verifier is None:
            assert self._factory is not None  # noqa: S101 - guaranteed by __init__
            self._verifier = self._factory()
        return self._verifier


def RequireCapability(  # noqa: N802 - a dependency factory, named like the thing it makes
    policy: CapabilityPolicy,
) -> Callable[[Request], Awaitable[CapabilityClaims]]:
    """
    Build a FastAPI dependency that admits only authorized callers.

    Usage:

        policy = CapabilityPolicy(verifier, scope="call:validate")

        @app.post("/validate")
        async def validate(
            body: ValidateRequest,
            claims: CapabilityClaims = Depends(RequireCapability(policy)),
        ) -> ValidateResponse:
            ...

    The dependency returns the verified claims, so a handler can read `claims.sub` to
    know *which* arm is calling and `claims.task_id` to attribute the work -- without
    trusting anything the body says about either.
    """

    async def dependency(request: Request) -> CapabilityClaims:
        token = bearer_token(request)
        request_id = getattr(request.state, "request_id", "unknown")

        # Token presence is checked FIRST, ahead of task binding. A caller with no
        # token at all must be told to obtain one (401) whatever else is missing from
        # the request; answering 403 because a header was absent would tell an
        # unauthenticated client that retrying is pointless, and it would collapse the
        # 401/403 distinction into "something was wrong".
        if not token:
            logger.warning("capability_denied", reason="missing_token", path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_body(
                    code="unauthenticated",
                    message="A capability token is required.",
                    request_id=request_id,
                ),
            )

        task_id: str | None = None
        if policy.bind_task:
            task_id = request.headers.get("x-task-id") or None
            if task_id is None:
                logger.warning(
                    "capability_denied", reason="missing_task_binding", path=request.url.path
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_body(
                        code="forbidden",
                        message="This endpoint requires a capability token bound to a task.",
                        request_id=request_id,
                    ),
                )

        try:
            verifier = policy.verifier
        except CapabilityConfigError as exc:
            # Not configured is not the same as not authorized. 503 tells an operator
            # to set a secret; 403 would tell a caller to find a better token.
            logger.error("capability_unconfigured", path=request.url.path, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_body(
                    code="unavailable",
                    message=(
                        "Capability tokens are not configured on this deployment, so "
                        "this endpoint is disabled. Set the capability signing secret "
                        "to enable it."
                    ),
                    request_id=request_id,
                ),
            ) from exc

        try:
            claims = await verifier.verify(
                token,
                required_scope=policy.scope,
                task_id=task_id,
            )
        except CapabilityDenied as exc:
            # The reason is logged here and deliberately not returned. See the module
            # docstring: the distinction is an oracle.
            logger.warning(
                "capability_denied",
                reason=exc.reason,
                detail=exc.detail,
                path=request.url.path,
                request_id=request_id,
            )
            missing = exc.reason == "missing_token"
            raise HTTPException(
                status_code=(
                    status.HTTP_401_UNAUTHORIZED if missing else status.HTTP_403_FORBIDDEN
                ),
                detail=error_body(
                    code="unauthenticated" if missing else "forbidden",
                    message=(
                        "A capability token is required."
                        if missing
                        else "The presented capability token does not authorize this request."
                    ),
                    request_id=request_id,
                ),
            ) from exc

        logger.debug(
            "capability_granted",
            caller=claims.sub,
            audience=claims.aud,
            task_id=claims.task_id,
            jti=claims.jti,
            path=request.url.path,
        )
        return claims

    return dependency
