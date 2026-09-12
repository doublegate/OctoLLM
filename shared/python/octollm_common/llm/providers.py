"""
The three real providers: Ollama, OpenAI, Anthropic.

Each is a thin adapter. The interesting content is where they *differ*, because those
differences are exactly what the protocol exists to hide from the arms:

| | structured output | embeddings |
|---|---|---|
| Ollama | `format=<json schema>` | `embed(model=, input=)` |
| OpenAI | `response_format={"type": "json_schema", ...}` | `embeddings.create(...)` |
| Anthropic | `output_config` | **none at all** |

Anthropic having no embeddings API is a permanent property, not an outage, so it
raises `EmbeddingsUnsupported` rather than a generic failure — a Retriever configured
against Anthropic must be pointed at another provider for `embed()`, and retrying
cannot help.

Imports are deferred into the constructors. The arms must start, and the whole test
suite must run, with none of these SDKs installed; a module-level import would make
`openai` a hard dependency of a stack whose entire point is that it runs without one.
"""

from __future__ import annotations

import json
from typing import Any, cast

from .base import Completion, EmbeddingsUnsupported, LLMError, Message, Usage

__all__ = ["AnthropicProvider", "OllamaProvider", "OpenAIProvider"]


def _split_system(messages: list[Message]) -> tuple[str | None, list[dict[str, str]]]:
    """Separate a leading system message; Anthropic takes it as its own parameter."""
    system: str | None = None
    rest: list[dict[str, str]] = []
    for message in messages:
        if message.role == "system" and system is None and not rest:
            system = message.content
        else:
            rest.append({"role": message.role, "content": message.content})
    return system, rest


def _parse_if_schema(text: str, schema: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Parse structured output, returning None when it is absent or malformed.

    Deliberately does not raise. `parsed is None` after requesting a schema tells the
    caller the model failed to produce structure -- which an arm can handle by
    retrying or degrading. Raising here would turn a recoverable model failure into
    a request failure.
    """
    if schema is None:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError, TypeError:
        return None
    return value if isinstance(value, dict) else None


class OllamaProvider:
    """Local models. The development default, because it needs no key and no network."""

    name = "ollama"

    def __init__(
        self,
        *,
        host: str = "http://localhost:11434",
        model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        try:
            from ollama import AsyncClient  # noqa: PLC0415
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise LLMError(self.name, "the `ollama` package is not installed") from exc
        self.model = model
        self.embedding_model = embedding_model
        self._client = AsyncClient(host=host)

    async def complete(
        self,
        messages: list[Message],
        *,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        try:
            response = await self._client.chat(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                # Ollama accepts a JSON Schema directly here, which constrains
                # decoding rather than merely requesting JSON.
                format=schema if schema else None,
                options={"temperature": temperature, "num_predict": max_tokens},
            )
        except Exception as exc:  # noqa: BLE001 - provider SDKs raise broadly
            raise LLMError(self.name, str(exc)) from exc

        text = response.message.content or ""
        return Completion(
            text=text,
            parsed=_parse_if_schema(text, schema),
            usage=Usage(
                provider=self.name,
                model=self.model,
                input_tokens=getattr(response, "prompt_eval_count", 0) or 0,
                output_tokens=getattr(response, "eval_count", 0) or 0,
            ),
            finish_reason=getattr(response, "done_reason", "stop") or "stop",
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.embed(model=self.embedding_model, input=texts)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(self.name, str(exc)) from exc
        return [list(vector) for vector in response.embeddings]

    async def aclose(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            await close()


class OpenAIProvider:
    """Opt-in. Requires a key; nothing in the default stack reaches it."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI  # noqa: PLC0415
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise LLMError(self.name, "the `openai` package is not installed") from exc
        self.model = model
        self.embedding_model = embedding_model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def complete(
        self,
        messages: list[Message],
        *,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        response_format: Any = None
        if schema is not None:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.get("title", "response"),
                    # Structured Outputs guarantees the shape rather than merely
                    # asking for JSON, which is the whole reason to prefer it over
                    # the older json_object mode.
                    "strict": True,
                    "schema": schema,
                },
            }

        # `cast` because the SDK types `messages` as a union of per-role TypedDicts
        # and cannot narrow a comprehension whose `role` is only known at runtime.
        # The dicts are the right shape; the type checker simply cannot see it.
        turns = cast("Any", [{"role": m.role, "content": m.content} for m in messages])

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=turns,
                temperature=temperature,
                max_tokens=max_tokens,
                **({"response_format": response_format} if response_format else {}),
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(self.name, str(exc)) from exc

        choice = response.choices[0]
        text = choice.message.content or ""
        usage = response.usage
        return Completion(
            text=text,
            parsed=_parse_if_schema(text, schema),
            usage=Usage(
                provider=self.name,
                model=self.model,
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
            finish_reason=choice.finish_reason or "stop",
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create(model=self.embedding_model, input=texts)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(self.name, str(exc)) from exc
        # Sorted by index: the API does not promise response order matches input order.
        return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]

    async def aclose(self) -> None:
        await self._client.close()


class AnthropicProvider:
    """Opt-in. Has no embeddings API, which `embed()` reports as a permanent fact."""

    name = "anthropic"

    def __init__(self, *, api_key: str, model: str = "claude-sonnet-5") -> None:
        try:
            from anthropic import AsyncAnthropic  # noqa: PLC0415
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise LLMError(self.name, "the `anthropic` package is not installed") from exc
        self.model = model
        # Named so the attribute exists for the protocol; every call raises.
        self.embedding_model = "<unsupported>"
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[Message],
        *,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        system, turns = _split_system(messages)

        extra: dict[str, Any] = {}
        if system is not None:
            extra["system"] = system
        if schema is not None:
            extra["output_config"] = {"format": {"type": "json_schema", "schema": schema}}

        # `temperature` is deliberately NOT sent. The Messages API of anthropic>=1.5
        # does not accept it -- mypy caught the call as unmatched by any overload, and
        # the installed SDK's signature confirms the parameter is gone. Passing it
        # would be a 400 on every request. The protocol keeps the argument because the
        # other two providers honour it; here it is accepted and ignored, which is
        # better than an adapter that silently rejects a supported call.
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=cast("Any", turns),
                **extra,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(self.name, str(exc)) from exc

        # `content` is a list of blocks; only the text ones carry the answer, and a
        # response may lead with a thinking or tool_use block.
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return Completion(
            text=text,
            parsed=_parse_if_schema(text, schema),
            usage=Usage(
                provider=self.name,
                model=self.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            finish_reason=response.stop_reason or "stop",
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingsUnsupported(self.name)

    async def aclose(self) -> None:
        await self._client.close()
