"""
Capability tokens: the authorization currency of the Neural Ring.

Until this module existed, capability isolation was 87KB of design document and zero
lines of code, while `docs/api/openapi/executor.yaml` already required a capability
token on every request. A contract that demands a credential no component can mint is
not a security control; it is a comment.

## The shape of the grant

A capability token is a short-lived JWT that says exactly one thing:

    "The orchestrator permits <sub> to call <aud>, for task <task_id>,
     within <scope>, at most <max_calls> times, until <exp>."

Every one of those is a narrowing. The token is not an identity and carries no
standing authority: it cannot be refreshed, it names a single callee, and it dies in
at most `MAX_TTL_SECONDS`. A compromised Coder holding a live token can reach the
Judge, for one task, five times, for two minutes -- and nothing else.

## The orchestrator is the sole signing authority

No arm mints a token, which is why `CapabilityIssuer` and `CapabilityVerifier` are
separate classes rather than one symmetric object. An arm image constructs a verifier;
only the orchestrator constructs an issuer. They happen to share a secret because
HS256 is symmetric, and that is a real limitation worth stating plainly: **any process
holding the verification secret could forge a token.** The mitigation today is that
arms are the only verifiers and they are inside the trust boundary; the fix is
asymmetric signing, and `kid` exists from day one so that migration is a key-map
change rather than a protocol change.

## Four things that are enforced here rather than assumed

- **`algorithms=["HS256"]` is passed explicitly on every decode.** Letting the token's
  own header choose the algorithm is the `alg: none` forgery, and the library will
  happily do it if asked loosely.
- **`kid` selects from a fixed allowlist**, never from the token. Reading an untrusted
  header to look up a key is fine; using it to *construct* a key path is how a signer
  gets pointed at a file it was never meant to read.
- **The secret is validated at construction, not at first use.** A service that starts
  with a placeholder secret and fails on the first real request has already told the
  orchestrator it is healthy. Both classes raise `CapabilityConfigError` in
  `__init__`, so the process dies at startup or not at all.
- **`max_calls` is counted by the callee**, through `CallCounter`. A bound the caller
  is trusted to respect is not a bound -- it is a request. See `CallCounter` for why
  the in-memory implementation is not sufficient for a replicated arm.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Protocol

import jwt
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "MAX_TTL_SECONDS",
    "MIN_SECRET_LENGTH",
    "CallCounter",
    "CapabilityClaims",
    "CapabilityConfigError",
    "CapabilityDenied",
    "CapabilityError",
    "CapabilityIssuer",
    "CapabilityVerifier",
    "InMemoryCallCounter",
    "PeerConstraints",
    "RedisCallCounter",
    "validate_secret",
]

#: The issuer refuses to mint anything longer-lived. The ring's peer loops are
#: sub-transactions inside a single graph node -- bounded by a deadline measured in
#: seconds -- so a token that outlives the node it was issued for is a token that can
#: only be used by something other than its purpose.
MAX_TTL_SECONDS = 120

#: HS256 keys shorter than the hash are trivially brute-forceable, and a short secret
#: is almost always a human-chosen one.
MIN_SECRET_LENGTH = 32

#: Values that appear in example configs and `.env.template` files. A deployment that
#: reaches production with one of these has not configured anything, and the failure
#: must be loud rather than a quietly forgeable token.
_PLACEHOLDER_SECRETS = frozenset(
    {
        "change_me",
        "changeme",
        "change-me",
        "placeholder",
        "secret",
        "supersecret",
        "your_secret_here",
        "octollm",
        "test",
        "development",
    }
)

_ISSUER = "orchestrator"

#: Every claim the verifier insists on seeing. Absent any one of them, the token
#: describes a grant with an unbounded dimension.
_REQUIRED_CLAIMS = ["iss", "sub", "aud", "exp", "iat", "nbf", "jti", "task_id", "scope"]

#: PyJWT exception -> stable denial slug. A mapping rather than a chain of `except`
#: clauses so the set of distinguishable failures is one readable list; anything not
#: named here collapses to `invalid_signature`, which is the safe default because it
#: is the least informative answer.
_DENIAL_REASONS: dict[type[Exception], str] = {
    jwt.ExpiredSignatureError: "expired",
    jwt.InvalidAudienceError: "wrong_audience",
    jwt.InvalidIssuerError: "wrong_issuer",
    jwt.MissingRequiredClaimError: "incomplete_grant",
    jwt.ImmatureSignatureError: "not_yet_valid",
}


class CapabilityError(Exception):
    """Base for everything this module raises."""


class CapabilityConfigError(CapabilityError):
    """
    The service is not configured to use capability tokens safely.

    Raised at construction so that a misconfigured deployment fails to start. It is
    deliberately not a subclass of `CapabilityDenied`: one is a bad request, the other
    is a bad deployment, and conflating them turns a 500-at-startup into a 403 that
    looks like someone else's problem.
    """


class CapabilityDenied(CapabilityError):
    """
    A presented token does not authorize what was attempted.

    Carries `reason` as a stable machine-readable slug. The HTTP layer maps this to
    401/403 and must **not** echo `detail` to the caller -- "signature invalid" versus
    "expired 3 seconds ago" is an oracle that helps forge the next attempt.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail or reason


def validate_secret(secret: str | None, *, purpose: str = "capability signing") -> str:
    """
    Accept a usable signing secret, or refuse to run.

    Raises:
        CapabilityConfigError: unset, too short, or a recognisable placeholder.
    """
    if not secret:
        raise CapabilityConfigError(
            f"No {purpose} secret configured. Set it to at least "
            f"{MIN_SECRET_LENGTH} random characters; this service will not start "
            "without one, because the alternative is issuing forgeable tokens."
        )
    if len(secret) < MIN_SECRET_LENGTH:
        raise CapabilityConfigError(
            f"The {purpose} secret is {len(secret)} characters; "
            f"at least {MIN_SECRET_LENGTH} are required for HS256."
        )
    if secret.strip().lower() in _PLACEHOLDER_SECRETS:
        raise CapabilityConfigError(
            f"The {purpose} secret is a known placeholder value. "
            "Generate one, for example with `openssl rand -hex 32`."
        )
    return secret


class PeerConstraints(BaseModel):
    """The quantitative half of a grant."""

    model_config = ConfigDict(extra="forbid")

    max_calls: int = Field(
        5,
        ge=1,
        le=100,
        description="How many times this token may be presented, counted by the callee",
    )
    max_tokens: int | None = Field(
        None, ge=1, description="Model-token ceiling the callee should respect"
    )


class CapabilityClaims(BaseModel):
    """
    The decoded, verified body of a capability token.

    Returned by `CapabilityVerifier.verify`. Nothing constructs this from untrusted
    input except that method, so any code holding one is holding a grant that has
    already been checked.
    """

    model_config = ConfigDict(extra="forbid")

    iss: str = Field(..., description="Always 'orchestrator'")
    sub: str = Field(..., description="The arm permitted to call")
    aud: str = Field(..., description="The arm permitted to be called")
    task_id: str = Field(..., description="The single task this grant covers")
    scope: list[str] = Field(default_factory=list, description="Permitted actions")
    constraints: PeerConstraints = Field(default_factory=PeerConstraints)
    jti: str = Field(..., description="Unique id; the key the callee counts calls under")
    iat: int = Field(..., description="Issued at, epoch seconds")
    nbf: int = Field(..., description="Not before, epoch seconds")
    exp: int = Field(..., description="Expires, epoch seconds")

    def permits(self, scope: str) -> bool:
        return scope in self.scope


class CallCounter(Protocol):
    """
    Counts how many times a token has been presented.

    `increment` returns the count **including** the current call, so the first
    presentation of a token returns 1.

    The counter must outlive the token, not the request, which is why `ttl_seconds` is
    a parameter: the entry may be dropped once the token has expired, and not before.
    """

    async def increment(self, jti: str, *, ttl_seconds: int) -> int: ...


class InMemoryCallCounter:
    """
    A per-process counter.

    **Correct only for a single replica.** Two replicas of the same arm each keep their
    own count, so a token bounded at five calls can be spent five times against each --
    the bound degrades to `max_calls x replicas`. That is a real weakening and the
    reason `RedisCallCounter` exists; this implementation is for tests and for
    single-instance development, and `create_arm_app` warns when it falls back to it.
    """

    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}

    async def increment(self, jti: str, *, ttl_seconds: int) -> int:
        now = time.time()
        # Prune opportunistically. The map is bounded by the number of tokens issued
        # within MAX_TTL_SECONDS, which is small, so a sweep here is cheaper than a
        # background task and cannot leak on an idle process.
        if self._counts:
            self._counts = {k: v for k, v in self._counts.items() if v[1] > now}
        count, expires_at = self._counts.get(jti, (0, now + ttl_seconds))
        count += 1
        self._counts[jti] = (count, expires_at)
        return count


class RedisCallCounter:
    """
    A counter shared by every replica of an arm.

    `INCR` is atomic, so concurrent presentations of the same token cannot both see a
    count below the bound. The `EXPIRE` is set only on the first increment: refreshing
    it on every call would let a token that is presented steadily keep its counter
    alive indefinitely, which costs memory but, more importantly, hides the fact that
    the counter's lifetime is supposed to be the token's.
    """

    def __init__(self, redis: Any, *, prefix: str = "octollm:cap:calls") -> None:
        self._redis = redis
        self._prefix = prefix

    async def increment(self, jti: str, *, ttl_seconds: int) -> int:
        key = f"{self._prefix}:{jti}"
        count = int(await self._redis.incr(key))
        if count == 1:
            await self._redis.expire(key, ttl_seconds)
        return count


class CapabilityIssuer:
    """
    Mints capability tokens. Constructed only by the orchestrator.

    Args:
        secret: The active signing secret. Validated here, not at first use.
        kid: Identifies the active key so a rotation can be rolled out without a
            flag day -- verifiers accept both keys during the overlap, then the old
            one is dropped.
        issuer: The `iss` claim. Overridable only so tests can prove a verifier
            rejects a foreign issuer.
    """

    def __init__(self, secret: str, *, kid: str, issuer: str = _ISSUER) -> None:
        self._secret = validate_secret(secret)
        if not kid:
            raise CapabilityConfigError(
                "A key id (kid) is required. It costs nothing today and is what makes "
                "key rotation, and the eventual move to asymmetric signing, a "
                "configuration change rather than a protocol change."
            )
        self._kid = kid
        self._issuer = issuer

    @property
    def kid(self) -> str:
        return self._kid

    def issue(
        self,
        *,
        caller: str,
        callee: str,
        task_id: str,
        scope: list[str],
        constraints: PeerConstraints | None = None,
        ttl_seconds: int = 60,
        now: int | None = None,
    ) -> str:
        """
        Mint one grant.

        Args:
            caller: The arm permitted to call. Becomes `sub`.
            callee: The arm permitted to be called. Becomes `aud`, which is what stops
                a token minted for the Judge from being presented to the Executor.
            task_id: The single task this grant covers.
            scope: Permitted actions, e.g. `["call:validate"]`.
            ttl_seconds: Clamped to `MAX_TTL_SECONDS`; longer is refused rather than
                silently shortened, because a caller asking for an hour has a different
                design in mind and should find out now.

        Raises:
            CapabilityConfigError: `ttl_seconds` exceeds the maximum.
            ValueError: empty caller, callee, task_id or scope.
        """
        if ttl_seconds > MAX_TTL_SECONDS:
            raise CapabilityConfigError(
                f"Requested a {ttl_seconds}s capability; the maximum is "
                f"{MAX_TTL_SECONDS}s. Peer loops are bounded sub-transactions inside "
                "one graph node, so a longer-lived grant outlives its purpose."
            )
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")
        if not caller or not callee:
            raise ValueError("caller and callee are both required")
        if caller == callee:
            # Not a security boundary, but a self-call through the ring is always a
            # bug: it is a function call that acquired a network hop and a token.
            raise ValueError(f"an arm cannot be issued a capability to call itself ({caller})")
        if not task_id:
            raise ValueError(
                "task_id is required: a grant that covers every task is standing authority"
            )
        if not scope:
            raise ValueError(
                "scope is required: an empty scope permits nothing, so minting one is a bug"
            )

        issued_at = int(time.time()) if now is None else now
        claims: dict[str, Any] = {
            "iss": self._issuer,
            "sub": caller,
            "aud": callee,
            "task_id": task_id,
            "scope": list(scope),
            "constraints": (constraints or PeerConstraints()).model_dump(),
            "jti": str(uuid.uuid4()),
            "iat": issued_at,
            "nbf": issued_at,
            "exp": issued_at + ttl_seconds,
        }
        return jwt.encode(claims, self._secret, algorithm="HS256", headers={"kid": self._kid})


class CapabilityVerifier:
    """
    Checks a presented token. Constructed by every callee.

    Args:
        keys: `kid` -> secret. A mapping rather than a single value so that a rotation
            has an overlap window in which both the old and new key verify.
        audience: This service's own id. A verifier that does not know who it is
            cannot reject a token minted for somebody else, which is the single most
            important check here.
        counter: Where `max_calls` is enforced. Required, with no default, because a
            forgotten counter silently removes the only non-cooperative bound in the
            design.
        leeway: Clock skew tolerance, in seconds. Small on purpose: the tokens live
            for at most two minutes, so generous leeway is a meaningful extension.
    """

    def __init__(
        self,
        keys: dict[str, str],
        *,
        audience: str,
        counter: CallCounter,
        issuer: str = _ISSUER,
        leeway: int = 5,
    ) -> None:
        if not keys:
            raise CapabilityConfigError("At least one verification key is required.")
        if not audience:
            raise CapabilityConfigError(
                "A verifier needs its own audience id, or it cannot tell a token "
                "minted for it from one minted for another arm."
            )
        for kid, secret in keys.items():
            if not kid:
                raise CapabilityConfigError("A verification key has an empty kid.")
            validate_secret(secret, purpose=f"capability verification (kid={kid})")
        self._keys = dict(keys)
        self._audience = audience
        self._counter = counter
        self._issuer = issuer
        self._leeway = leeway

    def _decode(self, token: str) -> CapabilityClaims:
        """
        Signature, key, liveness and shape. Everything cryptographic happens here.

        Split from `verify` so that the cryptographic checks and the authorization
        checks are separately readable: this method answers "is this token ours and
        intact", and `verify` answers "does it permit what was attempted".
        """
        if not token:
            raise CapabilityDenied("missing_token", "No capability token was presented.")

        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise CapabilityDenied("malformed_token", str(exc)) from exc

        # The kid selects from a fixed map built at construction. It is never used to
        # build a path, a URL, or anything else that leaves this dictionary.
        kid = header.get("kid")
        if not isinstance(kid, str) or kid not in self._keys:
            raise CapabilityDenied("unknown_key", f"No verification key for kid={kid!r}.")

        try:
            payload = jwt.decode(
                token,
                self._keys[kid],
                # Explicit, and never taken from the token's own header: that is the
                # `alg: none` forgery.
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as exc:
            raise CapabilityDenied(
                _DENIAL_REASONS.get(type(exc), "invalid_signature"), str(exc)
            ) from exc

        try:
            return CapabilityClaims.model_validate(payload)
        except ValueError as exc:
            # A well-signed token whose body we cannot parse is ours but wrong -- a
            # version skew between issuer and verifier. Denied, and worth an alert.
            raise CapabilityDenied("unparsable_grant", str(exc)) from exc

    async def verify(
        self,
        token: str,
        *,
        required_scope: str | None = None,
        task_id: str | None = None,
    ) -> CapabilityClaims:
        """
        Verify a token and charge one call against it.

        A successful return means: the signature is ours, the token is live, it names
        this service as its audience, it permits `required_scope`, it covers `task_id`,
        and it has not been spent past `constraints.max_calls`.

        Raises:
            CapabilityDenied: with a stable `reason` slug. The caller should log the
                slug and return a generic message.
        """
        claims = self._decode(token)

        if required_scope is not None and not claims.permits(required_scope):
            raise CapabilityDenied(
                "out_of_scope",
                f"Token scope {claims.scope} does not include {required_scope!r}.",
            )

        if task_id is not None and claims.task_id != task_id:
            # A live token for task A presented on task B is either a bug or lateral
            # movement, and both want the same answer.
            raise CapabilityDenied(
                "wrong_task",
                f"Token covers task {claims.task_id}, not {task_id}.",
            )

        remaining_ttl = max(1, claims.exp - int(time.time()))
        count = await self._counter.increment(claims.jti, ttl_seconds=remaining_ttl)
        if count > claims.constraints.max_calls:
            raise CapabilityDenied(
                "call_budget_exhausted",
                f"Token spent {count} times; the grant permits " f"{claims.constraints.max_calls}.",
            )

        return claims
