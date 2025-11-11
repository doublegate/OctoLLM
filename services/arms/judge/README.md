# Judge Arm

The Judge Arm validates outputs from other arms, ensuring quality and correctness.

## Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM**: GPT-3.5-turbo (validation-focused prompts)
- **Capabilities**: Output validation, quality scoring, acceptance criteria verification

## Validation Types

- **Syntax**: Code compilation, JSON validation
- **Semantic**: Requirement fulfillment, logic correctness
- **Security**: Vulnerability scanning, unsafe pattern detection
- **Performance**: Efficiency analysis, resource usage

## Development

```bash
cd services/arms/judge
poetry install
poetry run pytest tests/ -v
poetry run uvicorn src.main:app --reload --port 8004
```

## References

- [Judge Arm Specification](../../../docs/components/arms/judge.md)
- [Testing Strategy](../../../docs/testing/strategy.md)
