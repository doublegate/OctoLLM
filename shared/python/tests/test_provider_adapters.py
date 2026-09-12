"""
Tests for the three real provider adapters.

Each adapter is thin, and all of its risk sits in one place: the translation between
this protocol and an SDK whose shape differs from the other two. Those differences are
the whole reason the protocol exists, and they are easy to get subtly wrong in a way
no type checker catches -- a structured-output request that silently degrades to plain
JSON, an embedding list returned in response order rather than input order.

| | structured output | embeddings |
|---|---|---|
| Ollama | `format=<json schema>` | `embed(model=, input=)` |
| OpenAI | `response_format={"type": "json_schema", ...}` | `embeddings.create(...)` |
| Anthropic | `output_config` | **none at all** |

Every SDK here is replaced by a fake module in `sys.modules`, so these tests assert
what the adapter *sends* without a network, a key, or the real package installed. That
matters twice over: the provider SDKs are optional extras, so CI does not install
them, and a test that reached a real endpoint would not be a test.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from octollm_common.llm import (
    AnthropicProvider,
    EmbeddingsUnsupported,
    LLMError,
    Message,
    OllamaProvider,
    OpenAIProvider,
    create_provider,
)


class RecordingClient:
    """A stand-in SDK client that records its kwargs and returns a canned response."""

    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response

    async def close(self) -> None:
        self.closed = True


def _install(monkeypatch: pytest.MonkeyPatch, name: str, attr: str, factory: Any) -> None:
    """Put a fake SDK module where the adapter's deferred import will find it."""
    module = ModuleType(name)
    setattr(module, attr, factory)
    monkeypatch.setitem(sys.modules, name, module)


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


@pytest.fixture
def ollama(monkeypatch: pytest.MonkeyPatch) -> RecordingClient:
    chat = RecordingClient(
        response=SimpleNamespace(
            message=SimpleNamespace(content='{"verdict": "valid"}'),
            prompt_eval_count=11,
            eval_count=7,
            done_reason="stop",
        )
    )
    embed = RecordingClient(response=SimpleNamespace(embeddings=[[0.1, 0.2], [0.3, 0.4]]))
    client = SimpleNamespace(chat=chat, embed=embed, close=RecordingClient())
    _install(monkeypatch, "ollama", "AsyncClient", lambda **_: client)
    return client


async def test_ollama_passes_the_schema_as_format(ollama: RecordingClient):
    """
    `format=<json schema>` constrains decoding. Passing the schema in the prompt
    instead would make structured output a request rather than a guarantee.
    """
    provider = OllamaProvider()

    completion = await provider.complete([Message("user", "validate")], schema={"type": "object"})

    assert ollama.chat.calls[0]["format"] == {"type": "object"}
    assert completion.parsed == {"verdict": "valid"}
    assert completion.usage.input_tokens == 11
    assert completion.usage.output_tokens == 7


async def test_ollama_sends_no_format_when_no_schema_was_asked_for(ollama: RecordingClient):
    provider = OllamaProvider()

    completion = await provider.complete([Message("user", "chat")])

    assert ollama.chat.calls[0]["format"] is None
    assert completion.parsed is None, "structure is never invented"


async def test_ollama_embeds_through_the_embed_endpoint(ollama: RecordingClient):
    provider = OllamaProvider()

    vectors = await provider.embed(["a", "b"])

    assert ollama.embed.calls[0]["input"] == ["a", "b"]
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


async def test_ollama_wraps_a_transport_failure_in_llm_error(monkeypatch: pytest.MonkeyPatch):
    """
    The provider name rides along on the error so a retry can route elsewhere rather
    than hammering the backend that just failed.
    """
    client = SimpleNamespace(chat=RecordingClient(error=ConnectionError("refused")))
    _install(monkeypatch, "ollama", "AsyncClient", lambda **_: client)

    with pytest.raises(LLMError, match="ollama: refused") as caught:
        await OllamaProvider().complete([Message("user", "hi")])

    assert caught.value.provider == "ollama"


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


@pytest.fixture
def openai(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    create = RecordingClient(
        response=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"verdict": "valid"}'),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=13, completion_tokens=5),
        )
    )
    embeddings = RecordingClient(
        response=SimpleNamespace(
            # Deliberately out of order: the API does not promise response order
            # matches input order, and a retriever that trusted it would silently
            # attach every vector to the wrong document.
            data=[
                SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                SimpleNamespace(index=0, embedding=[0.1, 0.2]),
            ]
        )
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        embeddings=SimpleNamespace(create=embeddings),
        close=RecordingClient(),
    )
    _install(monkeypatch, "openai", "AsyncOpenAI", lambda **_: client)
    return client


async def test_openai_requests_strict_structured_output(openai: SimpleNamespace):
    """
    `strict: True` with a json_schema response format is what guarantees the shape.
    The older `json_object` mode only promises valid JSON, which an arm cannot parse
    into its contract model.
    """
    provider = OpenAIProvider(api_key="test-key-not-real")

    completion = await provider.complete(
        [Message("user", "validate")], schema={"title": "verdict", "type": "object"}
    )

    sent = openai.chat.completions.create.calls[0]["response_format"]
    assert sent["type"] == "json_schema"
    assert sent["json_schema"]["strict"] is True
    assert sent["json_schema"]["name"] == "verdict"
    assert completion.parsed == {"verdict": "valid"}
    assert completion.usage.input_tokens == 13


async def test_openai_omits_response_format_entirely_when_unstructured(
    openai: SimpleNamespace,
):
    """Sending `response_format: None` is an API error, not a no-op."""
    await OpenAIProvider(api_key="test-key-not-real").complete([Message("user", "chat")])

    assert "response_format" not in openai.chat.completions.create.calls[0]


async def test_openai_returns_embeddings_in_input_order(openai: SimpleNamespace):
    vectors = await OpenAIProvider(api_key="test-key-not-real").embed(["first", "second"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]], "sorted by index, not by arrival"


async def test_openai_wraps_a_failure(monkeypatch: pytest.MonkeyPatch):
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=RecordingClient(error=RuntimeError("429")))
        )
    )
    _install(monkeypatch, "openai", "AsyncOpenAI", lambda **_: client)

    with pytest.raises(LLMError, match="openai: 429"):
        await OpenAIProvider(api_key="test-key-not-real").complete([Message("user", "hi")])


async def test_openai_closes_its_client(openai: SimpleNamespace):
    provider = OpenAIProvider(api_key="test-key-not-real")

    await provider.aclose()

    assert openai.close.calls == [{}], "the underlying client is released, not leaked"


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


@pytest.fixture
def anthropic(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    create = RecordingClient(
        response=SimpleNamespace(
            content=[
                # A response may lead with a non-text block; concatenating everything
                # blindly would splice reasoning into the answer.
                SimpleNamespace(type="thinking", thinking="considering"),
                SimpleNamespace(type="text", text='{"verdict": '),
                SimpleNamespace(type="text", text='"valid"}'),
            ],
            usage=SimpleNamespace(input_tokens=17, output_tokens=3),
            stop_reason="end_turn",
        )
    )
    client = SimpleNamespace(
        messages=SimpleNamespace(create=create),
        close=RecordingClient(),
    )
    _install(monkeypatch, "anthropic", "AsyncAnthropic", lambda **_: client)
    return client


async def test_anthropic_lifts_the_system_message_out_of_the_turns(
    anthropic: SimpleNamespace,
):
    """
    Anthropic takes the system prompt as its own parameter. Left in `messages` it is
    rejected outright, so this translation is load-bearing rather than stylistic.
    """
    provider = AnthropicProvider(api_key="test-key-not-real")

    await provider.complete([Message("system", "you are a judge"), Message("user", "validate")])

    sent = anthropic.messages.create.calls[0]
    assert sent["system"] == "you are a judge"
    assert sent["messages"] == [{"role": "user", "content": "validate"}]


async def test_anthropic_passes_a_schema_as_output_config(anthropic: SimpleNamespace):
    provider = AnthropicProvider(api_key="test-key-not-real")

    completion = await provider.complete([Message("user", "validate")], schema={"type": "object"})

    config = anthropic.messages.create.calls[0]["output_config"]
    assert config["format"]["type"] == "json_schema"
    assert completion.parsed == {"verdict": "valid"}


async def test_anthropic_concatenates_only_the_text_blocks(anthropic: SimpleNamespace):
    completion = await AnthropicProvider(api_key="test-key-not-real").complete(
        [Message("user", "validate")]
    )

    assert completion.text == '{"verdict": "valid"}'
    assert "considering" not in completion.text
    assert completion.finish_reason == "end_turn"
    assert completion.usage.input_tokens == 17


async def test_anthropic_omits_system_and_output_config_when_neither_applies(
    anthropic: SimpleNamespace,
):
    await AnthropicProvider(api_key="test-key-not-real").complete([Message("user", "hi")])

    sent = anthropic.messages.create.calls[0]
    assert "system" not in sent
    assert "output_config" not in sent


async def test_anthropic_has_no_embeddings_api(anthropic: SimpleNamespace):
    """
    A permanent property of the provider, not an outage. A Retriever configured
    against Anthropic must be pointed elsewhere for `embed()`; retrying cannot help,
    which is why this is its own type.
    """
    with pytest.raises(EmbeddingsUnsupported):
        await AnthropicProvider(api_key="test-key-not-real").embed(["text"])


async def test_anthropic_wraps_a_failure(monkeypatch: pytest.MonkeyPatch):
    client = SimpleNamespace(
        messages=SimpleNamespace(create=RecordingClient(error=RuntimeError("overloaded")))
    )
    _install(monkeypatch, "anthropic", "AsyncAnthropic", lambda **_: client)

    with pytest.raises(LLMError, match="anthropic: overloaded"):
        await AnthropicProvider(api_key="test-key-not-real").complete([Message("user", "hi")])


# ---------------------------------------------------------------------------
# The factory, with the force-fake flag off
# ---------------------------------------------------------------------------


@pytest.fixture
def unforced(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Drop the force-fake flag for the few tests that must exercise real routing.

    Safe only because every SDK in this module is a fake in `sys.modules`: the
    adapters are built, but nothing they hold can open a socket.
    """
    monkeypatch.delenv("OCTOLLM_FORCE_FAKE_LLM", raising=False)


@pytest.mark.usefixtures("unforced")
async def test_the_factory_builds_ollama_with_the_configured_model(
    ollama: RecordingClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OCTOLLM_LLM_PROVIDER", "ollama")

    provider = create_provider(model="qwen3")

    assert isinstance(provider, OllamaProvider)
    assert provider.model == "qwen3"


@pytest.mark.usefixtures("unforced")
def test_the_factory_builds_openai_from_the_environment_key(
    openai: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")

    assert isinstance(create_provider("openai"), OpenAIProvider)


@pytest.mark.usefixtures("unforced")
def test_the_factory_builds_anthropic_from_the_environment_key(
    anthropic: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    assert isinstance(create_provider("anthropic"), AnthropicProvider)


@pytest.mark.usefixtures("unforced")
def test_a_missing_anthropic_key_fails_loudly(anthropic: SimpleNamespace):
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY is not set"):
        create_provider("anthropic")


@pytest.mark.usefixtures("unforced")
def test_the_provider_name_is_case_and_whitespace_insensitive(openai: SimpleNamespace):
    """Config files acquire trailing whitespace; that should not select a provider."""
    assert create_provider("  OpenAI \n", api_key="test-key-not-real").name == "openai"


# ---------------------------------------------------------------------------
# Shared adapter behaviour
# ---------------------------------------------------------------------------


async def test_malformed_structured_output_leaves_parsed_none_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    A model that failed to produce structure is a recoverable model failure -- an arm
    can retry or degrade. Raising would turn it into a request failure, and a partial
    JSON string is exactly what a truncated response looks like.
    """
    client = SimpleNamespace(
        chat=RecordingClient(
            response=SimpleNamespace(
                message=SimpleNamespace(content='{"verdict": "val'),
                prompt_eval_count=1,
                eval_count=1,
                done_reason="length",
            )
        )
    )
    _install(monkeypatch, "ollama", "AsyncClient", lambda **_: client)

    completion = await OllamaProvider().complete(
        [Message("user", "validate")], schema={"type": "object"}
    )

    assert completion.parsed is None
    assert completion.finish_reason == "length"


async def test_a_json_array_is_not_accepted_as_a_parsed_object(
    monkeypatch: pytest.MonkeyPatch,
):
    """`parsed` is typed `dict | None`; a list must not slip through it."""
    client = SimpleNamespace(
        chat=RecordingClient(
            response=SimpleNamespace(
                message=SimpleNamespace(content="[1, 2, 3]"),
                prompt_eval_count=1,
                eval_count=1,
                done_reason="stop",
            )
        )
    )
    _install(monkeypatch, "ollama", "AsyncClient", lambda **_: client)

    completion = await OllamaProvider().complete([Message("user", "x")], schema={"type": "array"})

    assert completion.parsed is None
