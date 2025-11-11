# Coder Arm

The Coder Arm generates, debugs, and refactors code across multiple programming languages.

## Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM**: GPT-4 (code-specific models)
- **Languages**: Python, Rust, JavaScript, TypeScript, Go, Bash

## Capabilities

- Code generation from natural language
- Bug fixing with test case validation
- Refactoring for performance/readability
- Test generation (unit, integration)
- Code review and suggestions

## Development

```bash
cd services/arms/coder
poetry install
poetry run pytest tests/ -v
poetry run uvicorn src.main:app --reload --port 8003
```

## References

- [Coder Arm Specification](../../../docs/components/arms/coder.md)
- [Code Quality Standards](../../../docs/engineering/coding-standards.md)
