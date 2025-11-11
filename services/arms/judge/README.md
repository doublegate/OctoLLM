# Judge Arm

The Judge Arm validates outputs, scores confidence, and ensures quality assurance across all arm results.

## Features

- Output validation against acceptance criteria
- Confidence scoring (0.0-1.0)
- Quality metrics calculation
- Failure detection and reporting
- Multi-dimensional evaluation

## Architecture

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM**: GPT-3.5-turbo
- **Port**: 8050

## References

- [Component Specification](../../../docs/components/judge-arm.md)
- [Validation Strategies](../../../docs/architecture/validation-strategies.md)
