# Retriever Arm

The Retriever Arm performs hybrid search across knowledge bases, combining keyword and semantic search.

## Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Vector DB**: Qdrant 1.7+
- **Search**: BM25 (keyword) + HNSW (semantic)
- **Embeddings**: OpenAI text-embedding-ada-002

## Capabilities

- Semantic search over documentation
- Code search (function definitions, usage examples)
- Historical task search (past solutions)
- Real-time indexing

## Development

```bash
cd services/arms/retriever
poetry install
poetry run pytest tests/ -v
poetry run uvicorn src.main:app --reload --port 8002
```

## References

- [Retriever Arm Specification](../../../docs/components/arms/retriever.md)
- [Memory Systems](../../../docs/implementation/memory-systems.md)
