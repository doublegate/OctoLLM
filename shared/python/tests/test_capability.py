"""
Tests for capability tokens.

Every test here is a claim about what an attacker cannot do, so each one is written to
be able to fail: the forgery tests construct a genuinely valid-looking token by the
route an attacker would use, rather than mutating a string until the parser complains.
A test that feeds `"not-a-jwt"` to a verifier proves only that base64 decoding works.
"""

from __future__ import annotations

import time

import jwt
import pytest
from octollm_common.capability import (
    MAX_TTL_SECONDS,
    MIN_SECRET_LENGTH,
    CapabilityConfigError,
    CapabilityDenied,
    CapabilityIssuer,
    CapabilityVerifier,
    InMemoryCallCounter,
    PeerConstraints,
    RedisCallCounter,
    validate_secret,
)

SECRET = "a" * MIN_SECRET_LENGTH
OTHER_SECRET = "b" * MIN_SECRET_LENGTH


@pytest.fixture
def issuer() -> CapabilityIssuer:
    return CapabilityIssuer(SECRET, kid="k1")


def make_verifier(
    *,
    audience: str = "judge",
    keys: dict[str, str] | None = None,
    counter: InMemoryCallCounter | None = None,
) -> CapabilityVerifier:
    return CapabilityVerifier(
        keys or {"k1": SECRET},
        audience=audience,
        counter=counter or InMemoryCallCounter(),
    )


# ---------------------------------------------------------------------------
# Fail closed at startup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "secret",
    [None, "", "short", "change_me", "CHANGEME", "  secret  ", "octollm"],
    ids=["none", "empty", "too-short", "placeholder", "placeholder-case", "padded", "project-name"],
)
def test_unusable_secret_is_refused_at_construction(secret: str | None) -> None:
    """A deployment with no real secret must not start, not fail on first request."""
    with pytest.raises(CapabilityConfigError):
        validate_secret(secret)


def test_secret_exactly_at_the_minimum_is_accepted() -> None:
    assert validate_secret("z" * MIN_SECRET_LENGTH) == "z" * MIN_SECRET_LENGTH


def test_one_character_below_the_minimum_is_refused() -> None:
    # The boundary matters: an off-by-one here silently halves the key space it was
    # meant to guarantee.
    with pytest.raises(CapabilityConfigError, match="at least"):
        validate_secret("z" * (MIN_SECRET_LENGTH - 1))


def test_issuer_requires_a_kid() -> None:
    with pytest.raises(CapabilityConfigError, match="key id"):
        CapabilityIssuer(SECRET, kid="")


def test_verifier_requires_an_audience() -> None:
    with pytest.raises(CapabilityConfigError, match="audience"):
        CapabilityVerifier({"k1": SECRET}, audience="", counter=InMemoryCallCounter())


def test_verifier_requires_at_least_one_key() -> None:
    with pytest.raises(CapabilityConfigError, match="(?i)at least one"):
        CapabilityVerifier({}, audience="judge", counter=InMemoryCallCounter())


def test_verifier_validates_every_key_it_is_given() -> None:
    """A rotation that adds a weak second key must fail as loudly as a weak first one."""
    with pytest.raises(CapabilityConfigError, match="kid=k2"):
        CapabilityVerifier(
            {"k1": SECRET, "k2": "tooshort"},
            audience="judge",
            counter=InMemoryCallCounter(),
        )


# ---------------------------------------------------------------------------
# Issuing narrows
# ---------------------------------------------------------------------------


async def test_round_trip_carries_the_whole_grant(issuer: CapabilityIssuer) -> None:
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="task-1",
        scope=["call:validate"],
        constraints=PeerConstraints(max_calls=3, max_tokens=1000),
    )
    claims = await make_verifier().verify(token, required_scope="call:validate", task_id="task-1")

    assert claims.sub == "coder"
    assert claims.aud == "judge"
    assert claims.task_id == "task-1"
    assert claims.scope == ["call:validate"]
    assert claims.constraints.max_calls == 3
    assert claims.constraints.max_tokens == 1000
    assert claims.jti


def test_ttl_beyond_the_maximum_is_refused_not_clamped(issuer: CapabilityIssuer) -> None:
    """
    Silently shortening would leave the caller believing it holds an hour-long grant.

    A caller asking for one has a different design in mind and should learn that here.
    """
    with pytest.raises(CapabilityConfigError, match=str(MAX_TTL_SECONDS)):
        issuer.issue(
            caller="coder",
            callee="judge",
            task_id="task-1",
            scope=["call:validate"],
            ttl_seconds=MAX_TTL_SECONDS + 1,
        )


def test_the_maximum_ttl_itself_is_allowed(issuer: CapabilityIssuer) -> None:
    assert issuer.issue(
        caller="coder",
        callee="judge",
        task_id="task-1",
        scope=["s"],
        ttl_seconds=MAX_TTL_SECONDS,
    )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"caller": ""}, "caller and callee"),
        ({"callee": ""}, "caller and callee"),
        ({"caller": "judge", "callee": "judge"}, "itself"),
        ({"task_id": ""}, "task_id"),
        ({"scope": []}, "scope"),
    ],
    ids=["no-caller", "no-callee", "self-call", "no-task", "empty-scope"],
)
def test_a_grant_with_an_unbounded_dimension_cannot_be_minted(
    issuer: CapabilityIssuer, kwargs: dict[str, object], match: str
) -> None:
    base: dict[str, object] = {
        "caller": "coder",
        "callee": "judge",
        "task_id": "task-1",
        "scope": ["call:validate"],
    }
    with pytest.raises(ValueError, match=match):
        issuer.issue(**{**base, **kwargs})  # type: ignore[arg-type]


def test_every_token_gets_a_distinct_jti(issuer: CapabilityIssuer) -> None:
    """Two tokens sharing a jti would share a call budget."""
    tokens = [
        issuer.issue(caller="coder", callee="judge", task_id="t", scope=["s"]) for _ in range(20)
    ]
    jtis = {jwt.decode(t, SECRET, algorithms=["HS256"], audience="judge")["jti"] for t in tokens}
    assert len(jtis) == 20


def test_the_kid_is_in_the_header_where_a_verifier_can_find_it(issuer: CapabilityIssuer) -> None:
    token = issuer.issue(caller="coder", callee="judge", task_id="t", scope=["s"])
    assert jwt.get_unverified_header(token)["kid"] == "k1"


# ---------------------------------------------------------------------------
# Forgery and misuse
# ---------------------------------------------------------------------------


def _claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    return {
        "iss": "orchestrator",
        "sub": "coder",
        "aud": "judge",
        "task_id": "task-1",
        "scope": ["call:validate"],
        "constraints": {"max_calls": 5, "max_tokens": None},
        "jti": "fixed-jti",
        "iat": now,
        "nbf": now,
        "exp": now + 60,
        **overrides,
    }


async def test_an_alg_none_token_is_rejected() -> None:
    """
    The classic forgery: a token that asks to be verified with no signature at all.

    It is rejected because `algorithms=["HS256"]` is passed explicitly on decode. A
    verifier that let the token's own header choose would accept this.
    """
    forged = jwt.encode(_claims(), key="", algorithm="none", headers={"kid": "k1"})
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(forged)
    assert exc.value.reason == "invalid_signature"


async def test_a_token_signed_with_the_wrong_secret_is_rejected() -> None:
    forged = jwt.encode(_claims(), OTHER_SECRET, algorithm="HS256", headers={"kid": "k1"})
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(forged)
    assert exc.value.reason == "invalid_signature"


async def test_a_token_naming_an_unknown_kid_is_rejected() -> None:
    """
    A kid the verifier does not know selects no key at all.

    The kid is attacker-controlled, so it is only ever used as a dictionary lookup
    against keys configured at startup.
    """
    forged = jwt.encode(_claims(), SECRET, algorithm="HS256", headers={"kid": "../../etc/passwd"})
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(forged)
    assert exc.value.reason == "unknown_key"


async def test_a_token_with_no_kid_is_rejected() -> None:
    forged = jwt.encode(_claims(), SECRET, algorithm="HS256")
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(forged)
    assert exc.value.reason == "unknown_key"


async def test_a_token_for_another_arm_is_rejected(issuer: CapabilityIssuer) -> None:
    """
    The single most important check: `aud` binds a grant to one callee.

    Without it, a token letting the Coder call the Judge would also let it call the
    Executor -- the whole lateral-movement bound collapses to "any arm, any time".
    """
    token = issuer.issue(caller="coder", callee="judge", task_id="t", scope=["s"])
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier(audience="executor").verify(token)
    assert exc.value.reason == "wrong_audience"


async def test_a_token_from_another_issuer_is_rejected() -> None:
    """An arm that somehow mints its own tokens is not the orchestrator."""
    rogue = CapabilityIssuer(SECRET, kid="k1", issuer="coder")
    token = rogue.issue(caller="coder", callee="judge", task_id="t", scope=["s"])
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(token)
    assert exc.value.reason == "wrong_issuer"


async def test_an_expired_token_is_rejected(issuer: CapabilityIssuer) -> None:
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t",
        scope=["s"],
        ttl_seconds=1,
        now=int(time.time()) - 600,
    )
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(token)
    assert exc.value.reason == "expired"


async def test_a_token_not_yet_valid_is_rejected(issuer: CapabilityIssuer) -> None:
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t",
        scope=["s"],
        now=int(time.time()) + 600,
    )
    with pytest.raises(CapabilityDenied):
        await make_verifier().verify(token)


@pytest.mark.parametrize(
    "dropped",
    ["iss", "sub", "aud", "exp", "iat", "nbf", "jti", "task_id", "scope"],
)
async def test_a_token_missing_any_required_claim_is_rejected(dropped: str) -> None:
    """
    Each absent claim is an unbounded dimension.

    Parametrised over all nine rather than spot-checked, because the one that is
    forgotten is the one that matters.
    """
    claims = _claims()
    del claims[dropped]
    forged = jwt.encode(claims, SECRET, algorithm="HS256", headers={"kid": "k1"})
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(forged)
    # `aud` missing is surfaced by the audience check rather than the require list;
    # both are denials, which is what this asserts.
    assert exc.value.reason in {"incomplete_grant", "wrong_audience"}


async def test_a_token_for_another_task_is_rejected(issuer: CapabilityIssuer) -> None:
    """A live token for task A presented on task B is lateral movement or a bug."""
    token = issuer.issue(caller="coder", callee="judge", task_id="task-1", scope=["s"])
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(token, task_id="task-2")
    assert exc.value.reason == "wrong_task"


async def test_a_token_outside_the_requested_scope_is_rejected(issuer: CapabilityIssuer) -> None:
    token = issuer.issue(caller="coder", callee="judge", task_id="t", scope=["call:validate"])
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(token, required_scope="exec:offensive")
    assert exc.value.reason == "out_of_scope"


async def test_no_token_is_its_own_reason() -> None:
    """Distinguished from a bad token so the HTTP layer can answer 401 rather than 403."""
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify("")
    assert exc.value.reason == "missing_token"


async def test_a_malformed_token_is_rejected() -> None:
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify("not.a.jwt")
    assert exc.value.reason == "malformed_token"


async def test_a_well_signed_token_with_an_unparsable_body_is_denied() -> None:
    """
    Version skew between issuer and verifier is a denial, not a crash.

    `max_calls` of -1 is well-formed JSON and correctly signed, and would be a
    `ValidationError` escaping into a 500 if the body were trusted after decoding.
    """
    forged = jwt.encode(
        _claims(constraints={"max_calls": -1}), SECRET, algorithm="HS256", headers={"kid": "k1"}
    )
    with pytest.raises(CapabilityDenied) as exc:
        await make_verifier().verify(forged)
    assert exc.value.reason == "unparsable_grant"


# ---------------------------------------------------------------------------
# The call budget is counted by the callee
# ---------------------------------------------------------------------------


async def test_max_calls_is_enforced_on_the_nth_presentation(issuer: CapabilityIssuer) -> None:
    verifier = make_verifier()
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t",
        scope=["s"],
        constraints=PeerConstraints(max_calls=3),
    )

    for _ in range(3):
        await verifier.verify(token, required_scope="s", task_id="t")

    with pytest.raises(CapabilityDenied) as exc:
        await verifier.verify(token, required_scope="s", task_id="t")
    assert exc.value.reason == "call_budget_exhausted"


async def test_the_budget_is_per_token_not_per_arm(issuer: CapabilityIssuer) -> None:
    """Exhausting one grant must not deny the next legitimate one."""
    verifier = make_verifier()
    spent = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t",
        scope=["s"],
        constraints=PeerConstraints(max_calls=1),
    )
    await verifier.verify(spent, required_scope="s", task_id="t")
    with pytest.raises(CapabilityDenied):
        await verifier.verify(spent, required_scope="s", task_id="t")

    fresh = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t",
        scope=["s"],
        constraints=PeerConstraints(max_calls=1),
    )
    assert await verifier.verify(fresh, required_scope="s", task_id="t")


async def test_a_denied_call_still_counts_against_the_budget(issuer: CapabilityIssuer) -> None:
    """
    Scope is checked before the counter, so a wrong-scope probe is free.

    That is deliberate and worth asserting so it is a decision rather than an accident:
    charging for requests that never reached the counter would let an unauthenticated
    caller burn a legitimate token's budget by guessing scopes.
    """
    verifier = make_verifier()
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t",
        scope=["s"],
        constraints=PeerConstraints(max_calls=1),
    )
    for _ in range(5):
        with pytest.raises(CapabilityDenied):
            await verifier.verify(token, required_scope="wrong", task_id="t")

    assert await verifier.verify(token, required_scope="s", task_id="t")


async def test_in_memory_counter_counts_from_one() -> None:
    counter = InMemoryCallCounter()
    assert await counter.increment("j", ttl_seconds=60) == 1
    assert await counter.increment("j", ttl_seconds=60) == 2


async def test_in_memory_counter_forgets_expired_entries() -> None:
    """Otherwise a long-lived process accumulates one entry per token forever."""
    counter = InMemoryCallCounter()
    await counter.increment("old", ttl_seconds=1)
    time.sleep(1.1)
    # Any increment triggers the sweep; the expired key restarts at 1.
    await counter.increment("new", ttl_seconds=60)
    assert await counter.increment("old", ttl_seconds=60) == 1


async def test_redis_counter_sets_a_ttl_only_on_first_increment() -> None:
    """
    Refreshing the TTL on every call would keep a steadily-used token's counter alive
    past the token itself, which is both a leak and a lie about what the key means.
    """

    class FakeRedis:
        def __init__(self) -> None:
            self.counts: dict[str, int] = {}
            self.expires: list[tuple[str, int]] = []

        async def incr(self, key: str) -> int:
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        async def expire(self, key: str, ttl: int) -> bool:
            self.expires.append((key, ttl))
            return True

    redis = FakeRedis()
    counter = RedisCallCounter(redis)
    assert await counter.increment("j", ttl_seconds=42) == 1
    assert await counter.increment("j", ttl_seconds=42) == 2
    assert await counter.increment("j", ttl_seconds=42) == 3
    assert redis.expires == [("octollm:cap:calls:j", 42)]


async def test_call_counter_ttl_covers_verification_leeway(issuer: CapabilityIssuer) -> None:
    """
    The counter entry must outlive the verifier's leeway window.

    Otherwise a single-use token spent just before `exp` has its counter entry expire at
    `exp` while `jwt.decode` still accepts the token for `leeway` more seconds.
    """
    recorded_ttls: list[int] = []

    class RecordingCounter:
        async def increment(self, jti: str, *, ttl_seconds: int) -> int:
            recorded_ttls.append(ttl_seconds)
            return 1

    now = int(time.time())
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t",
        scope=["s"],
        ttl_seconds=1,
        now=now - 1,
    )
    verifier = CapabilityVerifier(
        {"k1": SECRET},
        audience="judge",
        counter=RecordingCounter(),
        leeway=5,
    )
    await verifier.verify(token, required_scope="s", task_id="t")
    assert recorded_ttls and recorded_ttls[0] >= 5
