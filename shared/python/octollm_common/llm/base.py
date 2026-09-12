"""
The LLM provider boundary.

Every arm talks to a model through this protocol and nothing else. Three things
depend on that being the only door:

  * **The stack must run with no API keys.** `make up` and the whole test suite work
    against `FakeProvider`; OpenAI and Anthropic are opt-in, and Ollama is the local
    default for development.
  * **Tests must be deterministic.** A test that calls a real model is not a test, it
    is a sample. An autouse fixture forces the fake provider so that no test *can*
    reach the network.
  * **Spend must be observable.** Every completion returns `usage`, and it is
    load-bearing rather than decorative: once arms call each other directly over the
    Neural Ring (Stage 5), an arm's own response is the only place its peer's spend
    can be reported. Without a common usage object the orchestrator is structurally
    blind to everything spent off-graph.

Structured output is part of the protocol, not an afterthought. An arm that asks for
JSON gets a `schema` honoured by the provider's native mechanism -- Ollama's `format`,
OpenAI's `response_format: json_schema`, Anthropic's `output_config` -- rather than by
asking politely in a prompt and hoping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    """One turn. Deliberately minimal: providers differ, this does not."""

    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class Usage:
    """
    What one completion cost.

    `provider` and `model` are carried alongside the counts because a token is not a
    unit of money until you know which model produced it, and the budget ledger has
    to reconcile spend across providers within a single task.
    """

    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: Usage) -> Usage:
        """
        Accumulate spend across calls.

        Summing across providers collapses `provider`/`model` to "mixed", because a
        total that claims a single model would be a lie the budget ledger then
        reports upward.
        """
        if not isinstance(other, Usage):  # pragma: no cover - defensive
            return NotImplemented
        return Usage(
            provider=self.provider if self.provider == other.provider else "mixed",
            model=self.model if self.model == other.model else "mixed",
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass(frozen=True, slots=True)
class Completion:
    """
    One model response.

    `parsed` is populated only when a `schema` was requested AND the output validated
    against it. A caller that asked for structure and got `parsed is None` learns
    that the model failed to produce it, rather than receiving a plausible-looking
    dict assembled by the client.
    """

    text: str
    usage: Usage
    parsed: dict[str, Any] | None = None
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMError(RuntimeError):
    """A provider failed. Carries the provider name so a retry can route elsewhere."""

    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider


class EmbeddingsUnsupported(LLMError):
    """
    This provider has no embeddings API.

    A distinct type rather than a generic failure, because it is a permanent property
    of the provider and not a transient error: retrying, or failing over to another
    instance of the same provider, cannot help. Anthropic is the case that matters --
    it offers no embeddings endpoint at all, so a Retriever configured against it must
    be told to use a different provider for `embed()`, not to try again.
    """

    def __init__(self, provider: str) -> None:
        super().__init__(provider, "this provider has no embeddings API")


@runtime_checkable
class LLMProvider(Protocol):
    """What every arm may assume about a model backend, and nothing more."""

    name: str
    model: str
    embedding_model: str

    async def complete(
        self,
        messages: list[Message],
        *,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        """
        Generate one completion.

        Args:
            messages: The conversation. A leading `system` message is mapped to
                whatever the provider calls that concept.
            schema: A JSON Schema the output must satisfy. Honoured by the provider's
                native structured-output mechanism where one exists.
            temperature: Defaults to 0.0. Determinism is the useful default for a
                system whose outputs are validated by another arm.
            max_tokens: Hard ceiling on the response.

        Raises:
            LLMError: the provider failed.
        """
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed each text, returning one vector per input, in order.

        Raises:
            EmbeddingsUnsupported: this provider has no embeddings API.
            LLMError: the provider failed.
        """
        ...

    async def aclose(self) -> None:
        """Release the underlying client. Safe to call more than once."""
        ...
