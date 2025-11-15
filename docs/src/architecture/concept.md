# Core Concept

The biological inspiration behind OctoLLM's distributed architecture.

## Octopus Neurobiology

Octopuses have ~500 million neurons:
- **Central brain:** 40 million neurons (strategic planning)
- **Arms:** 240 million neurons distributed across 8 arms (local autonomy)
- **Reflex arcs:** Immediate responses without brain involvement

## Mapping to OctoLLM

- **Central Brain → Orchestrator:** Uses GPT-4/Claude Opus for strategic decisions
- **Arms → Specialized Modules:** Domain-specific processing with local LLMs
- **Reflex → Preprocessing Layer:** Fast pattern matching without LLM calls

For more details, see [ref-docs/OctoLLM-Concept_Idea.md](https://github.com/doublegate/OctoLLM/blob/main/ref-docs/OctoLLM-Concept_Idea.md).
