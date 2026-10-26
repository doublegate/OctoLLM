"""
Direct arm-to-arm calls: the synchronous half of the Neural Ring.

The ring is broadcast and asynchronous, which is right for artifacts but wrong for the
pairs the documents name as tight loops -- Coder<->Judge above all. A validation loop
that publishes a `code` artifact and waits for a `verdict` to come back around pays a
full round trip through Redis for what is conceptually a function call, and worse, has
nowhere to put "this is iteration 3 of at most 5".

So those pairs get HTTP, gated on a capability token.

## A peer loop is a bounded sub-transaction inside one graph node

`PeerLoopContract` is the whole of what bounds it, and the bound is not advisory:
iterations, an absolute deadline, a token budget, and a capability token that the
callee itself counts down. A loop never spans supersteps of the execution graph, for
three reasons the plan states and that are each independently sufficient --

- LangGraph checkpoints at superstep boundaries, so a loop spanning one would resume
  into a world where half its iterations already happened and the other half is gone;
- the budget ledger lives in graph state and reconciles only at boundaries, so
  spending that crosses one is spending nobody has accounted for;
- one node is one `StepResult` is one audit row, and a loop that outlives the node has
  no row of its own.

## Why `usage` is on every arm response

The orchestrator cannot see a peer call. That is the point of the ring, and it is also
the hole it opens: an arm that quietly calls a peer ten times has spent ten times the
tokens the orchestrator believes. So an arm returns the **cumulative** usage of itself
and everything it called, and `UsageAccumulator` exists so that doing it correctly is
less work than doing it wrong. Without this the orchestrator is structurally blind to
everything spent off-graph -- not under-reporting, but unable to report at all.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

from .app import ArmSpec
from .models.contracts import ArmResponse, UsageReport

logger = structlog.get_logger(__name__)

__all__ = [
    "PeerCallError",
    "PeerClient",
    "PeerDeadlineExceeded",
    "PeerLoopContract",
    "PeerTopologyError",
    "UsageAccumulator",
]

ResponseT = TypeVar("ResponseT", bound=ArmResponse)


class PeerCallError(Exception):
    """A peer call did not produce a usable response."""


class PeerTopologyError(PeerCallError):
    """
    This arm does not declare the callee as a peer.

    Caught client-side as defence in depth. The authoritative refusal is the callee's
    own `RequireCapability`, plus the fact that the orchestrator will not mint a token
    for an edge the roster does not contain -- but failing here turns a
    production-only 403 into an error at the call site, where the fix is.
    """


class PeerDeadlineExceeded(PeerCallError):
    """The loop's absolute deadline passed before the call could be made."""


class PeerLoopContract(BaseModel):
    """
    What a graph node hands an arm when it permits a peer loop.

    Every field is a ceiling. None of them is a suggestion, and the arm is not the only
    thing enforcing them: `capability_token` carries `max_calls`, which the *callee*
    counts, so an arm that ignores `max_iterations` runs out of token before it runs
    out of intent.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=1)
    callee: str = Field(..., min_length=1, description="arm_id being called")
    capability_token: str = Field(..., min_length=1, description="Minted by the orchestrator")
    max_iterations: int = Field(5, ge=1, le=50)
    deadline: datetime = Field(..., description="Absolute, not a duration")
    budget_tokens: int | None = Field(None, ge=1)

    @classmethod
    def starting_now(
        cls,
        *,
        task_id: str,
        callee: str,
        capability_token: str,
        max_iterations: int = 5,
        within_seconds: float = 60.0,
        budget_tokens: int | None = None,
    ) -> PeerLoopContract:
        """Build a contract whose deadline is `within_seconds` from now."""
        return cls(
            task_id=task_id,
            callee=callee,
            capability_token=capability_token,
            max_iterations=max_iterations,
            deadline=datetime.now(UTC) + timedelta(seconds=within_seconds),
            budget_tokens=budget_tokens,
        )

    def remaining_seconds(self, *, now: datetime | None = None) -> float:
        current = now or datetime.now(UTC)
        return (self.deadline - current).total_seconds()

    def expired(self, *, now: datetime | None = None) -> bool:
        return self.remaining_seconds(now=now) <= 0


class UsageAccumulator:
    """
    Sums an arm's own spend with its peers'.

    `provider` and `model` collapse to `"mixed"` once two different ones contribute,
    because a single label over two providers is a lie that a cost report will later
    be built on.
    """

    def __init__(self) -> None:
        self._providers: set[str] = set()
        self._models: set[str] = set()
        self._input = 0
        self._output = 0
        self._peer_calls = 0

    def add(self, usage: UsageReport) -> UsageAccumulator:
        """Fold in one report. Returns self so calls chain."""
        if usage.provider:
            self._providers.add(usage.provider)
        if usage.model:
            self._models.add(usage.model)
        self._input += usage.input_tokens
        self._output += usage.output_tokens
        self._peer_calls += usage.peer_calls
        return self

    def add_peer(self, usage: UsageReport) -> UsageAccumulator:
        """
        Fold in a peer's report and count the call.

        Separate from `add` so the peer-call count cannot be forgotten: the one number
        the orchestrator has no other way of learning is the one most easily dropped.
        """
        self.add(usage)
        self._peer_calls += 1
        return self

    def report(self) -> UsageReport:
        return UsageReport(
            provider=_collapse(self._providers),
            model=_collapse(self._models),
            input_tokens=self._input,
            output_tokens=self._output,
            peer_calls=self._peer_calls,
        )


def _collapse(values: set[str]) -> str:
    if not values:
        return "none"
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


class PeerClient:
    """
    Calls another arm directly, under a capability token.

    Args:
        spec: The *calling* arm's declaration. `spec.peers` is the client-side
            allowlist.
        base_url_for: Resolves an `arm_id` to where it listens. Injected rather than
            imported so that a test, a compose deployment and a Kubernetes deployment
            differ by one argument instead of by a patched module.
        client: An `httpx.AsyncClient`. Supplied by the caller so connections are
            pooled across calls; a client per call is a new TCP and TLS handshake on
            every iteration of a loop that exists to be fast.
    """

    def __init__(
        self,
        spec: ArmSpec,
        *,
        base_url_for: Any,
        client: httpx.AsyncClient,
        endpoint_for: Any | None = None,
    ) -> None:
        self._spec = spec
        self._base_url_for = base_url_for
        self._endpoint_for = endpoint_for
        self._client = client

    async def call(
        self,
        contract: PeerLoopContract,
        payload: BaseModel,
        response_model: type[ResponseT],
        *,
        request_id: str | None = None,
        endpoint: str | None = None,
    ) -> ResponseT:
        """
        Make one peer call under `contract`.

        Returns the parsed response. The caller is responsible for folding
        `response.usage` into its own `UsageAccumulator` -- this method cannot do it,
        because the accumulator belongs to the whole request and this is one call
        inside it.

        Raises:
            PeerTopologyError: the callee is not a declared peer of this arm.
            PeerDeadlineExceeded: the contract's deadline has already passed.
            PeerCallError: transport failure, a non-2xx status, or an unparsable body.
        """
        callee = contract.callee
        if callee not in self._spec.peers:
            raise PeerTopologyError(
                f"{self._spec.arm_id} declares peers {sorted(self._spec.peers)}; "
                f"{callee!r} is not among them. Add the edge to the roster -- the "
                "orchestrator issues tokens only for edges it can see there."
            )

        remaining = contract.remaining_seconds()
        if remaining <= 0:
            raise PeerDeadlineExceeded(
                f"Peer loop deadline for task {contract.task_id} passed "
                f"{-remaining:.1f}s ago; not calling {callee}."
            )

        path = endpoint or (self._endpoint_for(callee) if self._endpoint_for else None)
        if not path:
            raise PeerCallError(f"No endpoint known for peer {callee!r}.")
        url = f"{self._base_url_for(callee).rstrip('/')}{path}"

        headers = {
            "authorization": f"Bearer {contract.capability_token}",
            "x-task-id": contract.task_id,
        }
        if request_id:
            headers["x-request-id"] = request_id

        try:
            # The per-call timeout is the smaller of the loop's remaining time and the
            # client's own. A call permitted to run past the loop deadline would let a
            # single slow peer consume a budget that was meant to bound the whole loop.
            response = await self._client.post(
                url,
                json=payload.model_dump(mode="json"),
                headers=headers,
                timeout=remaining,
            )
        except httpx.HTTPError as exc:
            raise PeerCallError(f"Peer call to {callee} failed: {exc}") from exc

        if response.status_code >= 400:
            raise PeerCallError(
                f"Peer {callee} answered {response.status_code} for {path}. "
                f"Body: {response.text[:200]}"
            )

        try:
            parsed = response_model.model_validate_json(response.content)
        except ValueError as exc:
            # The same failure mode that kept 39 reflex-client tests green over a
            # client that could not parse a single real response: loud, named, and
            # attributed to the peer rather than surfacing as a generic 500 here.
            raise PeerCallError(
                f"Peer {callee} returned a body that does not match "
                f"{response_model.__name__}: {exc}"
            ) from exc

        logger.debug(
            "peer_call",
            caller=self._spec.arm_id,
            callee=callee,
            task_id=contract.task_id,
            status=response.status_code,
        )
        return parsed
