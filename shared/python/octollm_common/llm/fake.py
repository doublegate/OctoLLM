"""
A deterministic provider, so that tests are tests rather than samples.

`FakeProvider` is the default everywhere except a deliberately-configured deployment.
It never opens a socket, never needs a key, and returns the same thing for the same
input on every machine and every run.

## How a response is resolved

Four steps, in order, each a fallback for the one before:

1. **A scripted response.** `provider.script(prompt_contains="...", response=...)`
   registers an exact answer. This is how a test says "when the planner asks to
   decompose *this* goal, return *this* plan" without pretending to be a model.
2. **The prompt hash.** With no script, the response is derived from a hash of the
   messages, so the same prompt always yields the same text -- and two different
   prompts reliably yield different text, which is what makes a cache-hit assertion
   meaningful.
3. **Schema-valid synthesis.** When a `schema` is requested, an instance satisfying
   it is *constructed* -- correct types, required fields present, enums drawn from
   their own values, `minItems` honoured. A downstream `jsonschema` validation passes
   against the fake exactly as it would against a real model, so the validation path
   is exercised rather than skipped.
4. **Deterministic lorem.** A stable sentence, seeded by the same hash.

## Why `embed()` returns a unit vector

The retriever ranks by cosine similarity. A fake that returned zeros or random noise
would make ranking untestable -- every score identical, or different on every run.
These vectors are hash-derived and **L2-normalised**, so cosine similarity is just a
dot product, identical texts score exactly 1.0, and a golden ranking is stable across
machines. That is what lets Stage 8's retriever tests assert an *order*.

## The one thing this deliberately does not do

It does not pretend to be intelligent. A scripted response is the only way to get
meaningful content out of it, and that is on purpose: a fake that produced
plausible-looking answers would let a test assert on behaviour nothing implements.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from .base import Completion, EmbeddingsUnsupported, Message, Usage

__all__ = ["FakeProvider"]

_LOREM = (
    "the octopus arm acts locally",
    "a reflex needs no cognition",
    "the head plans and delegates",
    "provenance travels with the artifact",
    "a gate that cannot fail is not a gate",
    "measure before optimising",
)


def _digest(messages: list[Message], schema: dict[str, Any] | None) -> str:
    """A stable fingerprint of the whole request, including the schema."""
    payload = json.dumps(
        {
            "messages": [[m.role, m.content] for m in messages],
            "schema": schema,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _synthesise(schema: dict[str, Any], seed: str, _depth: int = 0) -> Any:
    """
    Build a value that satisfies `schema`.

    Not a general JSON Schema implementation -- it covers the constructs the arm
    contracts actually use. An unsupported construct returns a typed zero value
    rather than raising, because a fake provider failing a test for its own reasons
    teaches nothing about the code under test.
    """
    if _depth > 8:  # pragma: no cover - contracts are not this deep
        return None

    if enum := schema.get("enum"):
        # Deterministic choice, not the first: always picking [0] hides a bug where
        # the consumer only handles one variant.
        return enum[int(seed[_depth * 2 : _depth * 2 + 2] or "0", 16) % len(enum)]

    kind = schema.get("type")
    if isinstance(kind, list):  # e.g. ["string", "null"]
        kind = next((k for k in kind if k != "null"), "null")

    if kind == "object":
        properties: dict[str, Any] = schema.get("properties", {})
        required = schema.get("required", list(properties))
        return {
            name: _synthesise(properties[name], seed, _depth + 1)
            for name in required
            if name in properties
        }

    if kind == "array":
        items = schema.get("items", {"type": "string"})
        count = max(int(schema.get("minItems", 1)), 1)
        return [_synthesise(items, seed + str(i), _depth + 1) for i in range(count)]

    return _synthesise_scalar(kind, schema, seed)


def _synthesise_scalar(kind: str | None, schema: dict[str, Any], seed: str) -> Any:
    """
    The leaf types.

    Bounds are honoured rather than ignored: a `confidence` outside [0, 1] would fail
    the consumer's own validation, and a fake that trips the code under test for its
    own reasons teaches nothing.
    """
    if kind == "integer":
        low, high = int(schema.get("minimum", 0)), int(schema.get("maximum", 100))
        return low + int(seed[:4], 16) % max(high - low + 1, 1)

    if kind == "number":
        floor = float(schema.get("minimum", 0.0))
        ceiling = float(schema.get("maximum", 1.0))
        return round(floor + (int(seed[:8], 16) / 0xFFFFFFFF) * (ceiling - floor), 6)

    if kind == "boolean":
        return int(seed[:2], 16) % 2 == 0

    if kind == "null":
        return None

    # string, and anything unrecognised
    text = _LOREM[int(seed[:2], 16) % len(_LOREM)]
    if max_length := schema.get("maxLength"):
        text = text[: int(max_length)]
    return text


class FakeProvider:
    """A provider that answers from a script, a hash, or a schema -- never a network."""

    name = "fake"

    def __init__(self, *, model: str = "fake-1", embedding_dimensions: int = 384) -> None:
        self.model = model
        self.embedding_model = "fake-embed-1"
        self.embedding_dimensions = embedding_dimensions
        self._scripts: list[tuple[str, Any]] = []
        # Every call, in order. A test can assert what an arm asked for, which is
        # usually more interesting than what it received.
        self.calls: list[dict[str, Any]] = []

    # -- scripting ---------------------------------------------------------------

    def script(self, *, prompt_contains: str, response: str | dict[str, Any]) -> FakeProvider:
        """
        Register a canned answer for any prompt containing `prompt_contains`.

        Scripts are matched in registration order, so a later, more specific script
        must be registered before a broader one. Returns self, so registrations chain.
        """
        self._scripts.append((prompt_contains, response))
        return self

    def reset(self) -> None:
        """Drop scripts and recorded calls. The autouse fixture calls this per test."""
        self._scripts.clear()
        self.calls.clear()

    # -- the protocol ------------------------------------------------------------

    async def complete(
        self,
        messages: list[Message],
        *,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        prompt = "\n".join(m.content for m in messages)
        seed = _digest(messages, schema)
        self.calls.append(
            {
                "messages": [(m.role, m.content) for m in messages],
                "schema": schema,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )

        parsed: dict[str, Any] | None = None
        text: str | None = None

        for needle, response in self._scripts:
            if needle in prompt:
                if isinstance(response, dict):
                    parsed, text = response, json.dumps(response)
                else:
                    text = response
                break

        if text is None:
            if schema is not None:
                synthesised = _synthesise(schema, seed)
                parsed = synthesised if isinstance(synthesised, dict) else {"value": synthesised}
                text = json.dumps(parsed)
            else:
                text = f"{_LOREM[int(seed[:2], 16) % len(_LOREM)]} [{seed[:8]}]"

        # Token counts are a stable function of length, not a real tokeniser: the
        # budget ledger needs a number that moves with the work, and a fake that
        # claimed accuracy here would be worse than one that is obviously an estimate.
        return Completion(
            text=text,
            parsed=parsed,
            usage=Usage(
                provider=self.name,
                model=self.model,
                input_tokens=max(len(prompt) // 4, 1),
                output_tokens=max(len(text) // 4, 1),
            ),
            metadata={"seed": seed[:16], "scripted": bool(self._scripts) and parsed is not None},
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        """
        A hash-derived unit vector.

        Normalised so cosine similarity is a plain dot product and an identical text
        scores exactly 1.0 against itself -- which is the property that makes a golden
        ranking assertion possible at all.
        """
        # Normalising whitespace and case means "Hello  World" and "hello world"
        # embed identically, which is the behaviour a caller expects of an embedding
        # and which makes retrieval fixtures robust to incidental formatting.
        normalised = re.sub(r"\s+", " ", text.strip().lower())
        raw: list[float] = []
        counter = 0
        while len(raw) < self.embedding_dimensions:
            block = hashlib.sha256(f"{normalised}:{counter}".encode()).digest()
            raw.extend((byte - 127.5) / 127.5 for byte in block)
            counter += 1
        vector = raw[: self.embedding_dimensions]

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:  # pragma: no cover - impossible for sha256 output
            return [0.0] * self.embedding_dimensions
        return [value / norm for value in vector]

    async def aclose(self) -> None:
        return None


# Not a provider method: `embed()` returns unit vectors precisely so that similarity
# is this cheap, and keeping the helper here means a test never reimplements it.
def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity. A plain dot product for the unit vectors `embed()` returns."""
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} vs {len(b)}")
    return sum(x * y for x, y in zip(a, b, strict=True))


__all__ += ["EmbeddingsUnsupported", "cosine_similarity"]
