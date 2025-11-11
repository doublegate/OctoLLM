# Retriever Arm

The Retriever Arm performs knowledge base search, semantic retrieval, and contextual information gathering.

## Features

- Semantic search (Qdrant vector database)
- Keyword search (PostgreSQL full-text)
- Hybrid search strategies
- Context ranking and relevance scoring
- Knowledge graph traversal

## Architecture

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Databases**: Qdrant (vectors), PostgreSQL (metadata)
- **Port**: 8030

## References

- [Component Specification](../../../docs/components/retriever-arm.md)
- [Search Strategies](../../../docs/architecture/search-strategies.md)
- [Memory Systems](../../../docs/implementation/memory-systems.md)
