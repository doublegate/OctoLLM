# octollm-common

The shared framework for the eight arms and the orchestrator.

Eight services need the same five endpoints, the same error envelope, the same
correlation id, the same capability declaration and the same model backend. Written
eight times they drift eight ways. This is the one place they are written.

```bash
pip install -e "shared/python[dev]"     # or: make install
```

## What is in here

| Module | What it owns |
|---|---|
| `octollm_common.models.contracts` | Every arm's request and response models, defined **once** |
| `octollm_common.app` | `create_arm_app()` — health, ready, capabilities, metrics, and the arm's own endpoint |
| `octollm_common.errors` | One error envelope, **including FastAPI's 422** |
| `octollm_common.llm` | The provider protocol, `FakeProvider`, Ollama, OpenAI, Anthropic |

## The single-definition seam

`contracts.py` is imported by the arms as their FastAPI request and response models
*and* by the orchestrator as its client models. There is no second definition to drift
from, so a field rename is an error at import time rather than a 422 in production.

That is not a hypothetical concern in this repository. The orchestrator's reflex client
and the reflex layer maintained separate definitions of the same payload and disagreed
on four points at once; the client could not parse a single real response for the
entire life of both services, while 39 of its tests passed against mocks built from its
own models.

## No test can reach a model provider

`create_provider()` returns `FakeProvider` unless a provider is explicitly configured,
and the autouse fixture in `tests/conftest.py` sets `OCTOLLM_FORCE_FAKE_LLM=1`, which
overrides configuration entirely. Even a test that deliberately asks for `openai` gets
the fake.

The inversion is the point: in a stack that defaults to a real provider, forgetting to
configure a test means a network call, a bill, and a result that differs by machine.
Here, forgetting means the fake.

With the force flag off, a provider whose key is missing raises rather than degrading
to the fake — a deployment that believes it is calling a real model and is not would be
far worse than one that refuses to start.

## Provider SDKs are extras

```bash
pip install -e "shared/python[ollama]"      # local development default
pip install -e "shared/python[openai]"
pip install -e "shared/python[anthropic]"
```

An arm image that talks to Ollama has no reason to carry the OpenAI and Anthropic
SDKs, and the default install must be able to run the whole stack with no provider at
all. Each SDK is imported inside its provider's constructor, so an absent extra is an
error when you ask for that provider, never at import time.

**Anthropic has no embeddings API**, so `AnthropicProvider.embed()` raises
`EmbeddingsUnsupported` — a distinct type because it is a permanent property of the
provider rather than an outage, and retrying cannot help.

## Tests

```bash
make test-shared
```

Coverage is floored at 90%, higher than the orchestrator's 85%, because this package
is small, has no I/O in its default path, and is imported by nine services: a defect
here is nine services' defect.
