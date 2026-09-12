"""
Test configuration for the shared framework.

The autouse fixture below is the one that matters: it makes it **impossible** for a
test in this repository to reach a model provider over the network.

Setting `OCTOLLM_FORCE_FAKE_LLM=1` overrides configuration inside
`octollm_common.llm.create_provider`, so even a test that deliberately asks for
`openai` gets the fake. That is stronger than convention and stronger than care in
individual test files: a single forgotten `create_provider("openai")` in a fixture
would otherwise mean a network call, a bill, and a result that differs by machine and
by day.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _force_fake_llm() -> None:
    """No test may reach a real provider. Session-scoped so it is set before any import."""
    os.environ["OCTOLLM_FORCE_FAKE_LLM"] = "1"


@pytest.fixture(autouse=True)
def _no_provider_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Remove provider credentials from the environment for the duration of each test.

    Belt and braces alongside the force-fake flag. A developer with OPENAI_API_KEY
    exported should get exactly the same test results as CI, which has none -- and a
    test that accidentally constructs a real provider should fail loudly on the
    missing key rather than quietly succeed against a live endpoint.
    """
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST", "OCTOLLM_LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
