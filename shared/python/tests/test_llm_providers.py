"""
Tests for the LLM provider boundary.

The claims under test are the ones the rest of the plan depends on: the fake is
deterministic, it can satisfy a schema well enough that real validation passes, its
embeddings support a stable ranking, and no test can reach a network.
"""

from __future__ import annotations

import os

# An INDEPENDENT implementation of JSON Schema, not the one that synthesised the
# output. Imported at module scope rather than through `importorskip` on purpose: a
# skip that fires silently is a test that cannot fail, and this is the assertion the
# whole synthesis path exists to support.
import jsonschema
import pytest
from octollm_common.llm import (
    EmbeddingsUnsupported,
    FakeProvider,
    LLMError,
    Message,
    Usage,
    cosine_similarity,
    create_provider,
)

# ---------------------------------------------------------------------------
# No test may reach the network
# ---------------------------------------------------------------------------


def test_the_default_provider_is_the_fake():
    assert create_provider().name == "fake"


@pytest.mark.parametrize("kind", ["openai", "anthropic", "ollama"])
def test_a_real_provider_cannot_be_built_while_the_force_flag_is_set(kind: str):
    """
    The guarantee this whole fixture exists for.

    Even asking for a real provider by name returns the fake. Without this, one
    forgotten `create_provider("openai")` in a fixture is a network call, a bill, and
    a result that differs by machine.
    """
    assert os.environ["OCTOLLM_FORCE_FAKE_LLM"] == "1"
    assert create_provider(kind).name == "fake"


def test_a_missing_key_fails_loudly_rather_than_degrading_to_the_fake(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    With the force flag off, a provider that needs a key and has none must raise.

    Silently falling back to the fake would be far worse: a deployment would believe
    it was calling a real model, and every answer would be hash-derived lorem.
    """
    monkeypatch.delenv("OCTOLLM_FORCE_FAKE_LLM", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMError, match="OPENAI_API_KEY is not set"):
        create_provider("openai")


def test_an_unknown_provider_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OCTOLLM_FORCE_FAKE_LLM", raising=False)
    with pytest.raises(LLMError, match="unknown provider"):
        create_provider("gpt5-please")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


async def test_the_same_prompt_gives_the_same_answer():
    provider = FakeProvider()
    messages = [Message("user", "decompose: assess this repository")]

    first = await provider.complete(messages)
    second = await provider.complete(messages)

    assert first.text == second.text


async def test_different_prompts_give_different_answers():
    """
    Without this, a cache-hit assertion proves nothing: every prompt would look like
    a hit.
    """
    provider = FakeProvider()

    a = await provider.complete([Message("user", "decompose: assess repository A")])
    b = await provider.complete([Message("user", "decompose: assess repository B")])

    assert a.text != b.text


async def test_a_script_wins_over_the_hash():
    provider = FakeProvider().script(prompt_contains="decompose", response="step one: read")

    completion = await provider.complete([Message("user", "please decompose this goal")])

    assert completion.text == "step one: read"


async def test_a_dict_script_populates_parsed():
    provider = FakeProvider().script(
        prompt_contains="plan", response={"steps": [{"step_id": "s1"}]}
    )

    completion = await provider.complete([Message("user", "make a plan")])

    assert completion.parsed == {"steps": [{"step_id": "s1"}]}


async def test_calls_are_recorded_for_inspection():
    """What an arm asked for is usually more interesting than what it got back."""
    provider = FakeProvider()

    await provider.complete([Message("system", "you are a planner"), Message("user", "go")])

    assert len(provider.calls) == 1
    assert provider.calls[0]["messages"][0] == ("system", "you are a planner")


# ---------------------------------------------------------------------------
# Schema-valid synthesis
# ---------------------------------------------------------------------------


SCHEMA = {
    "type": "object",
    "title": "plan",
    "properties": {
        "rationale": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "step_count": {"type": "integer", "minimum": 1, "maximum": 9},
        "urgent": {"type": "boolean"},
        "verdict": {"enum": ["valid", "invalid", "needs_revision"]},
        "steps": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "properties": {"step_id": {"type": "string"}, "arm_id": {"type": "string"}},
                "required": ["step_id", "arm_id"],
            },
        },
    },
    "required": ["rationale", "confidence", "step_count", "urgent", "verdict", "steps"],
}


async def test_synthesised_output_actually_validates_against_the_schema():
    """
    The point of synthesis rather than lorem: a downstream `jsonschema` check passes
    against the fake exactly as it would against a real model, so the validation path
    is exercised instead of skipped.
    """
    provider = FakeProvider()

    completion = await provider.complete([Message("user", "plan it")], schema=SCHEMA)

    assert completion.parsed is not None
    jsonschema.validate(completion.parsed, SCHEMA)  # raises if invalid


async def test_synthesis_honours_bounds_and_enums():
    provider = FakeProvider()

    parsed = (await provider.complete([Message("user", "plan it")], schema=SCHEMA)).parsed

    assert parsed is not None
    assert 0.0 <= parsed["confidence"] <= 1.0
    assert 1 <= parsed["step_count"] <= 9
    assert parsed["verdict"] in {"valid", "invalid", "needs_revision"}
    assert len(parsed["steps"]) >= 2, "minItems honoured"
    assert isinstance(parsed["urgent"], bool)


async def test_synthesis_is_deterministic():
    provider = FakeProvider()
    messages = [Message("user", "plan it")]

    first = await provider.complete(messages, schema=SCHEMA)
    second = await provider.complete(messages, schema=SCHEMA)

    assert first.parsed == second.parsed


async def test_parsed_is_none_when_no_schema_was_requested():
    """A caller that did not ask for structure must not receive an invented dict."""
    provider = FakeProvider()

    assert (await provider.complete([Message("user", "hi")])).parsed is None


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


async def test_embeddings_are_unit_vectors():
    """
    Normalised so cosine similarity is a plain dot product and an identical text
    scores exactly 1.0 -- which is what makes a golden ranking assertion possible.
    """
    provider = FakeProvider()

    [vector] = await provider.embed(["the octopus arm acts locally"])

    assert len(vector) == 384
    assert cosine_similarity(vector, vector) == pytest.approx(1.0, abs=1e-9)


async def test_embeddings_are_deterministic_across_calls():
    provider = FakeProvider()

    first = await provider.embed(["distributed ai orchestration"])
    second = await FakeProvider().embed(["distributed ai orchestration"])

    assert first == second, "a different instance must embed identically"


async def test_embeddings_ignore_incidental_whitespace_and_case():
    provider = FakeProvider()

    [a], [b] = (
        await provider.embed(["Hello   World"]),
        await provider.embed(["hello world"]),
    )

    assert cosine_similarity(a, b) == pytest.approx(1.0, abs=1e-9)


async def test_different_texts_embed_differently_enough_to_rank():
    """
    A fake returning zeros or noise makes ranking untestable -- every score identical,
    or different every run. This is the property Stage 8's retriever tests rely on.
    """
    provider = FakeProvider()

    query, near, far = await provider.embed(["octopus", "octopus", "postgresql"])

    assert cosine_similarity(query, near) == pytest.approx(1.0, abs=1e-9)
    assert cosine_similarity(query, far) < 0.5


async def test_embed_returns_one_vector_per_input_in_order():
    provider = FakeProvider()
    texts = ["alpha", "beta", "gamma"]

    vectors = await provider.embed(texts)

    assert len(vectors) == 3
    for text, vector in zip(texts, vectors, strict=True):
        [alone] = await provider.embed([text])
        assert vector == alone, "order is preserved"


def test_cosine_similarity_rejects_a_dimension_mismatch():
    with pytest.raises(ValueError, match="dimension mismatch"):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------


async def test_usage_is_reported():
    provider = FakeProvider()

    usage = (await provider.complete([Message("user", "a reasonably long prompt")])).usage

    assert usage.provider == "fake"
    assert usage.input_tokens > 0
    assert usage.total_tokens == usage.input_tokens + usage.output_tokens


def test_usage_sums_and_collapses_provider_when_mixed():
    """
    A total claiming a single model when two were used would be a lie the budget
    ledger then reports upward.
    """
    a = Usage(provider="fake", model="fake-1", input_tokens=10, output_tokens=5)
    b = Usage(provider="ollama", model="llama3.2", input_tokens=3, output_tokens=2)

    total = a + b

    assert total.input_tokens == 13
    assert total.output_tokens == 7
    assert total.provider == "mixed"
    assert total.model == "mixed"


def test_usage_keeps_the_provider_when_it_is_the_same():
    a = Usage(provider="fake", model="fake-1", input_tokens=1)
    b = Usage(provider="fake", model="fake-1", output_tokens=1)

    assert (a + b).provider == "fake"


# ---------------------------------------------------------------------------
# Anthropic has no embeddings API
# ---------------------------------------------------------------------------


def test_embeddings_unsupported_is_a_distinct_permanent_error():
    """
    A distinct type because it is a permanent property, not an outage: retrying, or
    failing over to another instance of the same provider, cannot help. A Retriever
    configured against Anthropic must be pointed elsewhere for embed().
    """
    error = EmbeddingsUnsupported("anthropic")

    assert isinstance(error, LLMError)
    assert error.provider == "anthropic"
    assert "no embeddings api" in str(error).lower()
