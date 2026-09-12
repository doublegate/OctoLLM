"""
LLM providers, and the factory that chooses one.

The default is `fake` **everywhere except an explicitly configured deployment**. That
is the inversion that matters: a stack which defaults to a real provider is one where
forgetting to configure a test means a network call, a bill, and a non-deterministic
result. Here, forgetting means the fake.
"""

from __future__ import annotations

import os

from .base import (
    Completion,
    EmbeddingsUnsupported,
    LLMError,
    LLMProvider,
    Message,
    Role,
    Usage,
)
from .fake import FakeProvider, cosine_similarity
from .providers import AnthropicProvider, OllamaProvider, OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "Completion",
    "EmbeddingsUnsupported",
    "FakeProvider",
    "LLMError",
    "LLMProvider",
    "Message",
    "OllamaProvider",
    "OpenAIProvider",
    "Role",
    "Usage",
    "cosine_similarity",
    "create_provider",
]

#: Set by the autouse test fixture. When true, `create_provider` refuses to build
#: anything that can open a socket, whatever the configuration says.
_FORCE_FAKE_ENV = "OCTOLLM_FORCE_FAKE_LLM"


def create_provider(
    kind: str | None = None,
    *,
    model: str | None = None,
    api_key: str | None = None,
    host: str | None = None,
) -> LLMProvider:
    """
    Build the configured provider.

    Args:
        kind: `fake`, `ollama`, `openai` or `anthropic`. Defaults to
            `$OCTOLLM_LLM_PROVIDER`, then to `fake`.
        model: Override the provider's default model.
        api_key: Required for openai and anthropic; falls back to the usual
            environment variable.
        host: Ollama only.

    Raises:
        LLMError: an unknown provider, or a missing key for one that needs it. A
            missing key fails loudly rather than silently degrading to the fake --
            a deployment that believes it is calling a real model and is not would be
            far worse than one that refuses to start.
    """
    if os.getenv(_FORCE_FAKE_ENV) == "1":
        # The test suite sets this. It overrides configuration on purpose: a test
        # that reaches the network is not a test, and no amount of care in an
        # individual test file can prevent it as reliably as this can.
        return FakeProvider()

    kind = (kind or os.getenv("OCTOLLM_LLM_PROVIDER") or "fake").strip().lower()

    # An omitted `model` must leave each provider's own default in place rather than
    # overwrite it with None, so it is spread rather than passed.
    override: dict[str, str] = {"model": model} if model else {}

    if kind == "fake":
        # Spelled out rather than spread: `FakeProvider` also takes an int keyword,
        # and unpacking a `dict[str, str]` into it is not type-safe even though the
        # only key present is `model`.
        return FakeProvider(model=model) if model else FakeProvider()

    if kind == "ollama":
        return OllamaProvider(
            host=host or os.getenv("OLLAMA_HOST") or "http://localhost:11434",
            **override,
        )

    if kind == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("openai", "OPENAI_API_KEY is not set")
        return OpenAIProvider(api_key=key, **override)

    if kind == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("anthropic", "ANTHROPIC_API_KEY is not set")
        return AnthropicProvider(api_key=key, **override)

    raise LLMError(kind, "unknown provider; expected fake, ollama, openai or anthropic")
