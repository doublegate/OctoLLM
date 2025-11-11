# Phase 2: Core Capabilities

**Status**: Not Started
**Duration**: 8-10 weeks
**Team Size**: 4-5 engineers (3 Python, 1 Rust, 1 ML/data)
**Prerequisites**: Phase 1 complete
**Start Date**: TBD
**Target Completion**: TBD

---

## Overview

Phase 2 expands the OctoLLM system to include all 6 specialized arms, distributed memory systems, Kubernetes production deployment, and swarm decision-making capabilities. This phase transforms the POC into a production-capable system with all core functionality.

**Key Deliverables**:
1. Retriever Arm (Python) - Hybrid search with Qdrant + PostgreSQL
2. Coder Arm (Python) - Code generation with episodic memory
3. Judge Arm (Python) - Multi-layer output validation
4. Safety Guardian Arm (Python) - PII detection and content filtering
5. Distributed Memory System - PostgreSQL + Qdrant + Redis with routing
6. Kubernetes Production Deployment - StatefulSets, Deployments, HPA, Ingress
7. Swarm Decision-Making - Parallel proposal generation and consensus

**Success Criteria**:
- ✅ All 6 arms deployed and operational
- ✅ Memory system handling 100,000+ entities
- ✅ Kubernetes deployment with autoscaling
- ✅ Swarm decision-making working
- ✅ Load tests passing (1,000 concurrent tasks)
- ✅ Documentation updated

**Reference**: `docs/doc_phases/PHASE-2-COMPLETE-SPECIFICATIONS.md` (10,500+ lines)

---

## Sprint 2.1: Retriever Arm [Week 7-8]

**Duration**: 2 weeks
**Team**: 1-2 engineers (Python + ML)
**Prerequisites**: Phase 1 complete, Qdrant deployed
**Priority**: HIGH

### Sprint Goals

- Implement hybrid search (vector + keyword) with Reciprocal Rank Fusion
- Deploy Qdrant vector database with optimized collections
- Integrate semantic search with sentence-transformers
- Create knowledge base indexing pipeline
- Achieve >80% retrieval accuracy (relevant docs in top-5)
- Query latency <500ms for most queries

### Architecture Decisions Required

- [ ] **Decision 1: Embedding Model Selection**
  - Option A: sentence-transformers/all-MiniLM-L6-v2 (fast, 384 dim)
  - Option B: sentence-transformers/all-mpnet-base-v2 (better quality, 768 dim)
  - Option C: OpenAI text-embedding-ada-002 (API-based, 1536 dim)
  - **Recommendation**: Option A for cost/speed balance

- [ ] **Decision 2: Re-ranking Strategy**
  - Option A: Cross-encoder re-ranking (accurate but slow)
  - Option B: Reciprocal Rank Fusion (RRF) only (fast)
  - Option C: Hybrid approach (RRF + cross-encoder for top-10)
  - **Recommendation**: Option B initially, Option C for production

### Tasks

#### Qdrant Deployment and Configuration (8 hours)

- [ ] **Deploy Qdrant Vector Database** (4 hours)
  - Create Qdrant StatefulSet for Kubernetes:
    ```yaml
    # k8s/databases/qdrant-statefulset.yaml
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: qdrant
      namespace: octollm
    spec:
      serviceName: qdrant
      replicas: 1  # Single instance for Phase 2
      selector:
        matchLabels:
          app: qdrant
      template:
        metadata:
          labels:
            app: qdrant
        spec:
          containers:
          - name: qdrant
            image: qdrant/qdrant:v1.7.0
            ports:
            - containerPort: 6333
              name: http
            - containerPort: 6334
              name: grpc
            volumeMounts:
            - name: qdrant-storage
              mountPath: /qdrant/storage
            resources:
              requests:
                memory: "2Gi"
                cpu: "1000m"
              limits:
                memory: "4Gi"
                cpu: "2000m"
      volumeClaimTemplates:
      - metadata:
          name: qdrant-storage
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    ```
  - Create Qdrant Service (ClusterIP)
  - Verify deployment with health check
  - Files to create: `k8s/databases/qdrant-statefulset.yaml`, `k8s/databases/qdrant-service.yaml`
  - Reference: `docs/operations/kubernetes-deployment.md`

- [ ] **Create Collection Schema** (2 hours)
  - Define collection structure for documents:
    ```python
    # arms/retriever/collections.py
    from qdrant_client import QdrantClient
    from qdrant_client.http import models

    COLLECTION_CONFIG = {
        "documents": {
            "vector_size": 384,  # all-MiniLM-L6-v2
            "distance": "Cosine",
            "on_disk_payload": True,
            "hnsw_config": {
                "m": 16,
                "ef_construct": 100,
                "full_scan_threshold": 10000
            },
            "quantization_config": {
                "scalar": {
                    "type": "int8",
                    "quantile": 0.99,
                    "always_ram": True
                }
            }
        }
    }

    def initialize_collections(client: QdrantClient):
        """Initialize Qdrant collections with optimized configuration."""
        for collection_name, config in COLLECTION_CONFIG.items():
            if not client.collection_exists(collection_name):
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=config["vector_size"],
                        distance=models.Distance[config["distance"].upper()]
                    ),
                    hnsw_config=models.HnswConfigDiff(**config["hnsw_config"]),
                    quantization_config=models.ScalarQuantization(**config["quantization_config"]["scalar"]),
                    on_disk_payload=config["on_disk_payload"]
                )
    ```
  - Create indexes for metadata filtering
  - Configure HNSW parameters for performance
  - Files to create: `arms/retriever/collections.py`

- [ ] **Implement Qdrant Client Wrapper** (2 hours)
  - Connection pooling and retry logic
  - Health check integration
  - Batch operations for indexing
  - Code example:
    ```python
    # arms/retriever/qdrant_client.py
    from typing import List, Dict, Any
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    import asyncio
    from functools import lru_cache

    class QdrantClientWrapper:
        def __init__(self, url: str, api_key: str = None, timeout: int = 30):
            self.client = QdrantClient(url=url, api_key=api_key, timeout=timeout)

        async def search(
            self,
            collection_name: str,
            query_vector: List[float],
            limit: int = 10,
            filter_conditions: Dict = None,
            score_threshold: float = 0.0
        ) -> List[Dict[str, Any]]:
            """Async semantic search with optional filtering."""
            search_result = await asyncio.to_thread(
                self.client.search,
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=models.Filter(**filter_conditions) if filter_conditions else None,
                score_threshold=score_threshold,
                with_payload=True
            )
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in search_result
            ]
    ```
  - Files to create: `arms/retriever/qdrant_client.py`

#### Hybrid Search Implementation (12 hours)

- [ ] **Implement Semantic Search with Embeddings** (4 hours)
  - sentence-transformers integration
  - Batch embedding generation
  - Caching for common queries
  - Code example:
    ```python
    # arms/retriever/embeddings.py
    from sentence_transformers import SentenceTransformer
    from typing import List
    import torch
    from functools import lru_cache

    class EmbeddingGenerator:
        def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
            self.model = SentenceTransformer(model_name)
            self.model.eval()

        @lru_cache(maxsize=1000)
        def encode_cached(self, text: str) -> List[float]:
            """Generate embeddings with caching for common queries."""
            return self.encode([text])[0]

        def encode(self, texts: List[str]) -> List[List[float]]:
            """Generate embeddings for a batch of texts."""
            with torch.no_grad():
                embeddings = self.model.encode(
                    texts,
                    batch_size=32,
                    show_progress_bar=False,
                    normalize_embeddings=True
                )
            return embeddings.tolist()
    ```
  - Files to create: `arms/retriever/embeddings.py`
  - Reference: `docs/components/arms/retriever-arm.md`

- [ ] **Implement PostgreSQL Full-Text Search** (3 hours)
  - Create GIN indexes for text columns
  - ts_vector and ts_query integration
  - Relevance ranking with ts_rank
  - SQL schema:
    ```sql
    -- Add full-text search to entities table
    ALTER TABLE entities ADD COLUMN search_vector tsvector
      GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(properties::text, '')), 'C')
      ) STORED;

    CREATE INDEX entities_search_idx ON entities USING GIN (search_vector);

    -- Full-text search function
    CREATE OR REPLACE FUNCTION search_entities(query_text text, max_results int DEFAULT 20)
    RETURNS TABLE (
      entity_id uuid,
      name text,
      description text,
      relevance_score real
    ) AS $$
    BEGIN
      RETURN QUERY
      SELECT
        e.entity_id,
        e.name,
        e.description,
        ts_rank(e.search_vector, websearch_to_tsquery('english', query_text)) as relevance_score
      FROM entities e
      WHERE e.search_vector @@ websearch_to_tsquery('english', query_text)
      ORDER BY relevance_score DESC
      LIMIT max_results;
    END;
    $$ LANGUAGE plpgsql;
    ```
  - Files to create: `db/migrations/004_fulltext_search.sql`

- [ ] **Implement Reciprocal Rank Fusion (RRF)** (3 hours)
  - Combine vector and keyword search results
  - Configurable fusion weights
  - Deduplication logic
  - Code example:
    ```python
    # arms/retriever/fusion.py
    from typing import List, Dict, Any
    from collections import defaultdict

    class ReciprocalRankFusion:
        def __init__(self, k: int = 60):
            """
            Reciprocal Rank Fusion algorithm.
            k: constant for smoothing (typically 60)
            """
            self.k = k

        def fuse(
            self,
            semantic_results: List[Dict[str, Any]],
            keyword_results: List[Dict[str, Any]],
            semantic_weight: float = 0.6,
            keyword_weight: float = 0.4
        ) -> List[Dict[str, Any]]:
            """
            Fuse semantic and keyword search results using RRF.
            """
            scores = defaultdict(float)
            doc_map = {}

            # Process semantic results
            for rank, doc in enumerate(semantic_results, start=1):
                doc_id = doc["id"]
                scores[doc_id] += semantic_weight / (self.k + rank)
                doc_map[doc_id] = doc

            # Process keyword results
            for rank, doc in enumerate(keyword_results, start=1):
                doc_id = doc["id"]
                scores[doc_id] += keyword_weight / (self.k + rank)
                doc_map[doc_id] = doc

            # Sort by fused score
            sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            return [
                {
                    **doc_map[doc_id],
                    "fused_score": score,
                    "fusion_method": "RRF"
                }
                for doc_id, score in sorted_ids
            ]
    ```
  - Files to create: `arms/retriever/fusion.py`

- [ ] **Implement Context Ranking and Reranking** (2 hours)
  - Cross-encoder reranking (optional)
  - Maximal Marginal Relevance (MMR) for diversity
  - Relevance scoring thresholds
  - Code example:
    ```python
    # arms/retriever/reranking.py
    from typing import List, Dict, Any
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    class MaximalMarginalRelevance:
        def __init__(self, lambda_param: float = 0.5):
            """
            MMR for result diversification.
            lambda_param: 0=max diversity, 1=max relevance
            """
            self.lambda_param = lambda_param

        def rerank(
            self,
            query_embedding: List[float],
            documents: List[Dict[str, Any]],
            top_k: int = 10
        ) -> List[Dict[str, Any]]:
            """Apply MMR to diversify results."""
            if not documents:
                return []

            # Extract embeddings
            doc_embeddings = np.array([doc["embedding"] for doc in documents])
            query_emb = np.array([query_embedding])

            # Compute similarities
            query_sim = cosine_similarity(query_emb, doc_embeddings)[0]

            selected = []
            remaining = list(range(len(documents)))

            # Iterative selection
            while remaining and len(selected) < top_k:
                mmr_scores = []
                for i in remaining:
                    relevance = query_sim[i]

                    if selected:
                        selected_embs = doc_embeddings[selected]
                        diversity = max(cosine_similarity([doc_embeddings[i]], selected_embs)[0])
                    else:
                        diversity = 0

                    mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * diversity
                    mmr_scores.append((i, mmr_score))

                # Select best MMR score
                best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
                selected.append(best_idx)
                remaining.remove(best_idx)

            return [documents[i] for i in selected]
    ```
  - Files to create: `arms/retriever/reranking.py`

#### Retriever Arm Service Implementation (8 hours)

- [ ] **Create FastAPI Service Structure** (2 hours)
  - Service initialization and configuration
  - Dependency injection for clients
  - Health check endpoints
  - Files to create: `arms/retriever/main.py`, `arms/retriever/config.py`

- [ ] **Implement Hybrid Search Endpoint** (3 hours)
  - POST /search endpoint with query and filters
  - Pagination support
  - Response caching with Redis
  - Code example:
    ```python
    # arms/retriever/main.py
    from fastapi import FastAPI, HTTPException, Depends
    from pydantic import BaseModel, Field
    from typing import List, Dict, Any, Optional
    from .embeddings import EmbeddingGenerator
    from .qdrant_client import QdrantClientWrapper
    from .fusion import ReciprocalRankFusion
    from .reranking import MaximalMarginalRelevance
    import asyncio

    app = FastAPI(title="Retriever Arm")

    class SearchRequest(BaseModel):
        query: str = Field(..., min_length=1, max_length=1000)
        top_k: int = Field(default=10, ge=1, le=100)
        filters: Optional[Dict[str, Any]] = None
        enable_reranking: bool = Field(default=True)

    class SearchResponse(BaseModel):
        results: List[Dict[str, Any]]
        total_found: int
        search_time_ms: float

    @app.post("/search", response_model=SearchResponse)
    async def hybrid_search(request: SearchRequest):
        """Hybrid search combining semantic and keyword search."""
        import time
        start_time = time.time()

        # Generate query embedding
        embedding_gen = get_embedding_generator()
        query_embedding = embedding_gen.encode_cached(request.query)

        # Parallel search execution
        semantic_task = asyncio.create_task(
            semantic_search(query_embedding, request.top_k, request.filters)
        )
        keyword_task = asyncio.create_task(
            keyword_search(request.query, request.top_k, request.filters)
        )

        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )

        # Fuse results
        rrf = ReciprocalRankFusion(k=60)
        fused_results = rrf.fuse(
            semantic_results,
            keyword_results,
            semantic_weight=0.6,
            keyword_weight=0.4
        )

        # Optional reranking
        if request.enable_reranking:
            mmr = MaximalMarginalRelevance(lambda_param=0.7)
            fused_results = mmr.rerank(query_embedding, fused_results, request.top_k)

        search_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            results=fused_results[:request.top_k],
            total_found=len(fused_results),
            search_time_ms=search_time_ms
        )
    ```
  - Files to create: `arms/retriever/api/search.py`

- [ ] **Implement Document Indexing Endpoint** (2 hours)
  - POST /index endpoint for adding documents
  - Batch indexing support
  - Embedding generation and storage
  - Files to create: `arms/retriever/api/indexing.py`

- [ ] **Add Caching Layer with Redis** (1 hour)
  - Cache search results for common queries
  - TTL-based cache expiration (1 hour)
  - Cache key generation from query hash
  - Code example:
    ```python
    # arms/retriever/cache.py
    import hashlib
    import json
    from typing import Optional, Any
    import redis.asyncio as redis

    class SearchCache:
        def __init__(self, redis_url: str, ttl: int = 3600):
            self.redis = redis.from_url(redis_url)
            self.ttl = ttl

        def _generate_key(self, query: str, filters: dict = None) -> str:
            """Generate cache key from query and filters."""
            cache_input = {
                "query": query,
                "filters": filters or {}
            }
            cache_str = json.dumps(cache_input, sort_keys=True)
            return f"search_cache:{hashlib.sha256(cache_str.encode()).hexdigest()}"

        async def get(self, query: str, filters: dict = None) -> Optional[Any]:
            """Retrieve cached search results."""
            key = self._generate_key(query, filters)
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
            return None

        async def set(self, query: str, results: Any, filters: dict = None):
            """Cache search results."""
            key = self._generate_key(query, filters)
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(results)
            )
    ```
  - Files to create: `arms/retriever/cache.py`

### Testing Requirements

- [ ] **Unit Tests** (6 hours)
  - Test embedding generation (consistency, caching)
  - Test RRF fusion algorithm (correctness, edge cases)
  - Test MMR reranking (diversity improvement)
  - Test cache hit/miss scenarios
  - Target coverage: >85%
  - Test file: `arms/retriever/tests/test_retrieval.py`
  - Example tests:
    ```python
    # arms/retriever/tests/test_retrieval.py
    import pytest
    from retriever.fusion import ReciprocalRankFusion
    from retriever.embeddings import EmbeddingGenerator

    def test_rrf_fusion():
        """Test Reciprocal Rank Fusion combines results correctly."""
        rrf = ReciprocalRankFusion(k=60)

        semantic = [
            {"id": "doc1", "score": 0.95},
            {"id": "doc2", "score": 0.85},
            {"id": "doc3", "score": 0.75}
        ]

        keyword = [
            {"id": "doc2", "score": 0.90},
            {"id": "doc4", "score": 0.80},
            {"id": "doc1", "score": 0.70}
        ]

        fused = rrf.fuse(semantic, keyword)

        # doc2 should rank highest (appears in both)
        assert fused[0]["id"] == "doc2"
        assert "fused_score" in fused[0]

    def test_embedding_caching():
        """Test embedding caching improves performance."""
        gen = EmbeddingGenerator()

        import time
        # First call (uncached)
        start = time.time()
        emb1 = gen.encode_cached("test query")
        first_time = time.time() - start

        # Second call (cached)
        start = time.time()
        emb2 = gen.encode_cached("test query")
        second_time = time.time() - start

        # Cached call should be much faster
        assert second_time < first_time * 0.1
        assert emb1 == emb2
    ```

- [ ] **Integration Tests** (4 hours)
  - Test Qdrant integration (search, indexing)
  - Test PostgreSQL full-text search
  - Test end-to-end hybrid search flow
  - Test file: `tests/integration/test_retriever_integration.py`
  - Scenarios:
    - Document indexing → Search retrieval
    - Hybrid search with filters
    - Cache hit/miss behavior

### Documentation Deliverables

- [ ] **API Documentation** (2 hours)
  - OpenAPI spec for all endpoints (auto-generated by FastAPI)
  - Request/response examples
  - Error code reference
  - Files: Auto-generated at `/docs` endpoint

- [ ] **Component README** (1 hour)
  - Architecture overview
  - Configuration guide
  - Deployment instructions
  - Files to create: `arms/retriever/README.md`

### Success Criteria

- [ ] Hybrid search retrieves relevant documents >80% of time (top-5)
- [ ] Query latency P95 <500ms
- [ ] Cache hit rate >60% for common queries after warm-up
- [ ] All tests passing with >85% coverage
- [ ] API documentation complete
- [ ] Successfully integrated with Orchestrator

### Common Pitfalls & Tips

⚠️ **Pitfall 1**: Poor embedding quality leads to low retrieval accuracy
✅ **Solution**: Use high-quality embedding models (all-mpnet-base-v2) and normalize embeddings

⚠️ **Pitfall 2**: RRF weights favor one search method too heavily
✅ **Solution**: A/B test different weight combinations (0.5/0.5, 0.6/0.4, 0.7/0.3)

⚠️ **Pitfall 3**: Qdrant memory usage grows unbounded
✅ **Solution**: Enable quantization and on-disk payload storage

### Estimated Effort

- Development: 28 hours
- Testing: 10 hours
- Documentation: 3 hours
- **Total**: 41 hours (~2 weeks for 1 engineer)

### Dependencies

- Blocks: Sprint 2.3 (Judge arm needs retrieval for fact-checking)
- Blocked by: Phase 1 complete, Qdrant deployed

---

## Sprint 2.2: Coder Arm [Week 8-9]

**Duration**: 2 weeks
**Team**: 1-2 engineers (Python + LLM experience)
**Prerequisites**: Qdrant deployed, Memory systems basic structure
**Priority**: HIGH

### Sprint Goals

- Implement code generation with GPT-4/Claude integration
- Create episodic memory for code snippets (Qdrant-based)
- Add static analysis integration (Ruff for Python, Clippy for Rust)
- Implement debugging assistance
- Code refactoring suggestions
- Generated code passes linters >90% of time

### Architecture Decisions Required

- [ ] **Decision 1: LLM Model Selection**
  - Option A: GPT-4 (best quality, expensive)
  - Option B: GPT-3.5-turbo (fast, cheaper)
  - Option C: Claude 3 Sonnet (good balance)
  - **Recommendation**: GPT-4 for complex, GPT-3.5 for simple

- [ ] **Decision 2: Static Analysis Integration**
  - Option A: Pre-generation (analyze context before generation)
  - Option B: Post-generation (validate generated code)
  - Option C: Both (comprehensive but slower)
  - **Recommendation**: Option B for simplicity

### Tasks

#### Episodic Memory Setup (6 hours)

- [ ] **Create Qdrant Collection for Code Snippets** (2 hours)
  - Language-specific collections (Python, Rust, JavaScript)
  - Metadata schema (language, framework, complexity)
  - Code example:
    ```python
    # arms/coder/memory.py
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from typing import List, Dict, Any

    LANGUAGE_COLLECTIONS = {
        "python_code": {"vector_size": 384, "distance": "Cosine"},
        "rust_code": {"vector_size": 384, "distance": "Cosine"},
        "javascript_code": {"vector_size": 384, "distance": "Cosine"}
    }

    def initialize_code_collections(client: QdrantClient):
        """Initialize language-specific code collections."""
        for collection_name, config in LANGUAGE_COLLECTIONS.items():
            if not client.collection_exists(collection_name):
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=config["vector_size"],
                        distance=models.Distance[config["distance"].upper()]
                    ),
                    hnsw_config=models.HnswConfigDiff(m=16, ef_construct=100)
                )

                # Create payload indexes for filtering
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name="language",
                    field_schema="keyword"
                )
    ```
  - Files to create: `arms/coder/memory.py`

- [ ] **Implement CoderMemory Class** (4 hours)
  - Store code snippets with embeddings
  - Semantic search for similar code
  - Context retrieval for generation
  - Code example:
    ```python
    # arms/coder/memory.py (continued)
    from sentence_transformers import SentenceTransformer
    import uuid

    class CoderMemory:
        def __init__(self, qdrant_client: QdrantClient, embedding_model: str = "all-MiniLM-L6-v2"):
            self.client = qdrant_client
            self.model = SentenceTransformer(embedding_model)

        async def store_code_snippet(
            self,
            code: str,
            language: str,
            description: str,
            metadata: Dict[str, Any] = None
        ) -> str:
            """Store code snippet with embedding."""
            # Generate embedding from code + description
            text = f"{description}\n\n{code}"
            embedding = self.model.encode(text).tolist()

            snippet_id = str(uuid.uuid4())
            collection_name = f"{language.lower()}_code"

            self.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=snippet_id,
                        vector=embedding,
                        payload={
                            "code": code,
                            "language": language,
                            "description": description,
                            **(metadata or {})
                        }
                    )
                ]
            )

            return snippet_id

        async def search_similar_code(
            self,
            query: str,
            language: str,
            limit: int = 5
        ) -> List[Dict[str, Any]]:
            """Search for similar code snippets."""
            query_embedding = self.model.encode(query).tolist()
            collection_name = f"{language.lower()}_code"

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )

            return [
                {
                    "code": hit.payload["code"],
                    "description": hit.payload.get("description"),
                    "similarity": hit.score
                }
                for hit in results
            ]
    ```
  - Files to create: `arms/coder/memory.py`

#### LLM Integration for Code Generation (8 hours)

- [ ] **Implement OpenAI/Anthropic Code Generation** (4 hours)
  - GPT-4 integration with code-specific prompts
  - Claude 3 integration as fallback
  - Temperature and parameter tuning
  - Code example:
    ```python
    # arms/coder/generator.py
    from openai import AsyncOpenAI
    from anthropic import AsyncAnthropic
    from typing import Optional, Dict, Any

    class CodeGenerator:
        def __init__(self, openai_key: str, anthropic_key: str):
            self.openai = AsyncOpenAI(api_key=openai_key)
            self.anthropic = AsyncAnthropic(api_key=anthropic_key)

        async def generate_code(
            self,
            prompt: str,
            language: str,
            context: Optional[str] = None,
            model: str = "gpt-4"
        ) -> Dict[str, Any]:
            """Generate code using LLM."""
            system_prompt = f"""You are an expert {language} programmer.
Generate clean, idiomatic, well-documented {language} code.
Include type hints, error handling, and follow best practices.
"""

            if context:
                system_prompt += f"\n\nRelevant context:\n{context}"

            try:
                if model.startswith("gpt"):
                    response = await self.openai.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,  # Lower temp for code
                        max_tokens=2000
                    )

                    return {
                        "code": response.choices[0].message.content,
                        "model": model,
                        "tokens": response.usage.total_tokens
                    }
                else:
                    # Claude fallback
                    response = await self.anthropic.messages.create(
                        model="claude-3-sonnet-20240229",
                        max_tokens=2000,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )

                    return {
                        "code": response.content[0].text,
                        "model": "claude-3-sonnet",
                        "tokens": response.usage.input_tokens + response.usage.output_tokens
                    }
            except Exception as e:
                raise CodeGenerationError(f"Code generation failed: {str(e)}")
    ```
  - Files to create: `arms/coder/generator.py`

- [ ] **Implement Context-Aware Generation** (2 hours)
  - Retrieve similar code from memory
  - Include relevant examples in prompt
  - Improve generation quality with context

- [ ] **Add Token Usage Tracking** (2 hours)
  - Prometheus metrics for LLM API calls
  - Cost tracking per request
  - Rate limiting to prevent overuse

#### Static Analysis Integration (6 hours)

- [ ] **Integrate Python Linters (Ruff, Black)** (3 hours)
  - Post-generation validation
  - Automatic formatting
  - Error reporting
  - Code example:
    ```python
    # arms/coder/validators.py
    import subprocess
    import tempfile
    from pathlib import Path
    from typing import Dict, Any, List

    class PythonValidator:
        def validate_code(self, code: str) -> Dict[str, Any]:
            """Validate Python code with Ruff and Black."""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = Path(f.name)

            try:
                # Run Ruff for linting
                ruff_result = subprocess.run(
                    ['ruff', 'check', str(temp_path)],
                    capture_output=True,
                    text=True
                )

                # Run Black for formatting check
                black_result = subprocess.run(
                    ['black', '--check', str(temp_path)],
                    capture_output=True,
                    text=True
                )

                issues = []
                if ruff_result.returncode != 0:
                    issues.append({
                        "tool": "ruff",
                        "message": ruff_result.stdout
                    })

                if black_result.returncode != 0:
                    issues.append({
                        "tool": "black",
                        "message": "Code formatting issues detected"
                    })

                return {
                    "valid": len(issues) == 0,
                    "issues": issues
                }
            finally:
                temp_path.unlink()
    ```
  - Files to create: `arms/coder/validators.py`

- [ ] **Integrate Rust Linters (Clippy)** (2 hours)
  - Similar validation for Rust code
  - Cargo check integration

- [ ] **Add Syntax Validation** (1 hour)
  - AST parsing to verify syntax
  - Early error detection

#### Coder Arm Service Implementation (8 hours)

- [ ] **Create FastAPI Service** (2 hours)
  - Service initialization
  - Dependency injection
  - Health checks
  - Files to create: `arms/coder/main.py`

- [ ] **Implement /code Endpoint** (3 hours)
  - POST /code for code generation
  - Language and framework parameters
  - Context retrieval from memory
  - Validation and formatting
  - Code example:
    ```python
    # arms/coder/api/generation.py
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel, Field
    from typing import Optional, Dict, Any
    from ..generator import CodeGenerator
    from ..validators import PythonValidator, RustValidator
    from ..memory import CoderMemory

    router = APIRouter()

    class CodeRequest(BaseModel):
        prompt: str = Field(..., min_length=10, max_length=2000)
        language: str = Field(..., regex="^(python|rust|javascript|typescript)$")
        framework: Optional[str] = None
        include_context: bool = True
        validate: bool = True

    class CodeResponse(BaseModel):
        code: str
        language: str
        validation_result: Dict[str, Any]
        tokens_used: int
        similar_examples: List[Dict[str, Any]]

    @router.post("/code", response_model=CodeResponse)
    async def generate_code(request: CodeRequest):
        """Generate code based on natural language prompt."""
        # Retrieve similar code from memory
        similar_code = []
        if request.include_context:
            memory = get_coder_memory()
            similar_code = await memory.search_similar_code(
                query=request.prompt,
                language=request.language,
                limit=3
            )

        # Build context from similar examples
        context = "\n\n".join([
            f"Example {i+1}:\n{ex['code']}"
            for i, ex in enumerate(similar_code)
        ])

        # Generate code
        generator = get_code_generator()
        result = await generator.generate_code(
            prompt=request.prompt,
            language=request.language,
            context=context if similar_code else None
        )

        # Validate generated code
        validation_result = {"valid": True, "issues": []}
        if request.validate:
            if request.language == "python":
                validator = PythonValidator()
                validation_result = validator.validate_code(result["code"])
            elif request.language == "rust":
                validator = RustValidator()
                validation_result = validator.validate_code(result["code"])

        # Store in memory if valid
        if validation_result["valid"]:
            memory = get_coder_memory()
            await memory.store_code_snippet(
                code=result["code"],
                language=request.language,
                description=request.prompt
            )

        return CodeResponse(
            code=result["code"],
            language=request.language,
            validation_result=validation_result,
            tokens_used=result["tokens"],
            similar_examples=similar_code
        )
    ```
  - Files to create: `arms/coder/api/generation.py`

- [ ] **Implement /debug Endpoint** (2 hours)
  - POST /debug for debugging assistance
  - Error analysis and suggestions
  - Files to create: `arms/coder/api/debugging.py`

- [ ] **Implement /refactor Endpoint** (1 hour)
  - POST /refactor for code improvements
  - Refactoring suggestions
  - Files to create: `arms/coder/api/refactoring.py`

### Testing Requirements

- [ ] **Unit Tests** (6 hours)
  - Test code generation quality (syntax correctness)
  - Test memory retrieval (similar code search)
  - Test validators (catch syntax errors)
  - Target coverage: >85%
  - Test file: `arms/coder/tests/test_generation.py`

- [ ] **Integration Tests** (4 hours)
  - Test end-to-end code generation flow
  - Test memory integration
  - Test validation pipeline
  - Scenarios:
    - Generate Python function → Validate → Store
    - Search similar code → Generate with context

### Documentation Deliverables

- [ ] **API Documentation** (2 hours)
  - OpenAPI spec
  - Code generation examples
  - Best practices

- [ ] **Component README** (1 hour)
  - Architecture overview
  - Supported languages
  - Configuration guide
  - Files to create: `arms/coder/README.md`

### Success Criteria

- [ ] Generated code passes linters >90% of time
- [ ] Memory retrieval finds relevant examples
- [ ] Static analysis integrated
- [ ] All tests passing with >85% coverage
- [ ] API documentation complete

### Common Pitfalls & Tips

⚠️ **Pitfall 1**: Generated code has syntax errors
✅ **Solution**: Use temperature=0.2 and validate with AST parsing

⚠️ **Pitfall 2**: Context retrieval returns irrelevant examples
✅ **Solution**: Fine-tune embedding model on code corpus

⚠️ **Pitfall 3**: High LLM API costs
✅ **Solution**: Use GPT-3.5-turbo for simple tasks, cache results

### Estimated Effort

- Development: 28 hours
- Testing: 10 hours
- Documentation: 3 hours
- **Total**: 41 hours (~2 weeks for 1 engineer)

### Dependencies

- Blocks: Sprint 2.7 (Swarm needs multiple arms operational)
- Blocked by: Qdrant deployed, basic memory structure

---

## Sprint 2.3: Judge Arm [Week 9-10]

**Duration**: 2 weeks
**Team**: 1 engineer (Python + ML)
**Prerequisites**: Retriever Arm complete (for fact-checking)
**Priority**: HIGH

### Sprint Goals

- Implement multi-layer validation (schema, facts, criteria, hallucination)
- Create quality scoring system with weighted rubrics
- Integrate with Retriever for fact-checking
- Implement hallucination detection
- Generate actionable feedback for failed validations
- Validation catches >95% of schema errors, >90% fact accuracy

### Architecture Decisions Required

- [ ] **Decision 1: Hallucination Detection Method**
  - Option A: NLI (Natural Language Inference) model
  - Option B: Fact extraction + verification against retrieval
  - Option C: LLM-based consistency checking
  - **Recommendation**: Option B for explainability

- [ ] **Decision 2: Scoring Methodology**
  - Option A: Binary pass/fail
  - Option B: Weighted rubric (0-100 score)
  - Option C: Multi-dimensional scoring
  - **Recommendation**: Option B for flexibility

### Tasks

#### Validation Framework (8 hours)

- [ ] **Implement Schema Validation** (2 hours)
  - Pydantic model validation
  - JSON schema validation
  - Custom validators
  - Code example:
    ```python
    # arms/judge/validators/schema.py
    from pydantic import BaseModel, ValidationError, validator
    from typing import Any, Dict, List
    import jsonschema

    class SchemaValidator:
        def validate_pydantic(self, data: Dict, model_class: type) -> Dict[str, Any]:
            """Validate data against Pydantic model."""
            try:
                validated = model_class(**data)
                return {
                    "valid": True,
                    "validated_data": validated.dict(),
                    "errors": []
                }
            except ValidationError as e:
                return {
                    "valid": False,
                    "validated_data": None,
                    "errors": [
                        {
                            "field": err["loc"][0] if err["loc"] else "root",
                            "message": err["msg"],
                            "type": err["type"]
                        }
                        for err in e.errors()
                    ]
                }

        def validate_json_schema(self, data: Dict, schema: Dict) -> Dict[str, Any]:
            """Validate data against JSON schema."""
            try:
                jsonschema.validate(instance=data, schema=schema)
                return {
                    "valid": True,
                    "errors": []
                }
            except jsonschema.exceptions.ValidationError as e:
                return {
                    "valid": False,
                    "errors": [
                        {
                            "field": ".".join(str(p) for p in e.path),
                            "message": e.message,
                            "schema_path": ".".join(str(p) for p in e.schema_path)
                        }
                    ]
                }
    ```
  - Files to create: `arms/judge/validators/schema.py`

- [ ] **Implement Fact-Checking** (3 hours)
  - Extract claims from output
  - Verify against Retriever knowledge base
  - k-evidence rule (require k=3 supporting documents)
  - Code example:
    ```python
    # arms/judge/validators/facts.py
    from typing import List, Dict, Any
    import re
    from retriever.client import RetrieverClient

    class FactChecker:
        def __init__(self, retriever_client: RetrieverClient, k: int = 3):
            """
            Fact checker with k-evidence rule.
            k: number of supporting documents required
            """
            self.retriever = retriever_client
            self.k = k

        def extract_claims(self, text: str) -> List[str]:
            """Extract factual claims from text."""
            # Simple heuristic: sentences with specific entities or numbers
            sentences = re.split(r'[.!?]+', text)
            claims = []

            for sentence in sentences:
                sentence = sentence.strip()
                # Claims often contain specific details
                if any([
                    re.search(r'\d+', sentence),  # Numbers
                    re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+', sentence),  # Proper nouns
                    any(word in sentence.lower() for word in ['is', 'was', 'are', 'were'])  # Assertions
                ]):
                    claims.append(sentence)

            return claims

        async def verify_claim(self, claim: str) -> Dict[str, Any]:
            """Verify a single claim against knowledge base."""
            # Search for supporting evidence
            search_results = await self.retriever.search(
                query=claim,
                top_k=10
            )

            # Count supporting vs contradicting documents
            supporting = []
            contradicting = []

            for result in search_results:
                # Simple similarity threshold
                if result["score"] > 0.7:
                    supporting.append(result)
                elif result["score"] < 0.3:
                    contradicting.append(result)

            verified = len(supporting) >= self.k

            return {
                "claim": claim,
                "verified": verified,
                "supporting_count": len(supporting),
                "supporting_docs": supporting[:3],  # Top 3
                "confidence": len(supporting) / self.k if self.k > 0 else 0
            }

        async def check_facts(self, text: str) -> Dict[str, Any]:
            """Check all factual claims in text."""
            claims = self.extract_claims(text)

            if not claims:
                return {
                    "valid": True,
                    "message": "No factual claims to verify",
                    "claims_checked": 0
                }

            # Verify all claims
            results = [await self.verify_claim(claim) for claim in claims]

            verified_count = sum(1 for r in results if r["verified"])
            accuracy = verified_count / len(results) if results else 0

            return {
                "valid": accuracy >= 0.8,  # 80% threshold
                "accuracy": accuracy,
                "claims_checked": len(results),
                "claims_verified": verified_count,
                "failed_claims": [r for r in results if not r["verified"]]
            }
    ```
  - Files to create: `arms/judge/validators/facts.py`

- [ ] **Implement Acceptance Criteria Checking** (2 hours)
  - Compare output against task acceptance criteria
  - Rule-based validation
  - LLM-based semantic validation
  - Code example:
    ```python
    # arms/judge/validators/criteria.py
    from typing import List, Dict, Any
    from openai import AsyncOpenAI

    class CriteriaChecker:
        def __init__(self, openai_client: AsyncOpenAI):
            self.client = openai_client

        async def check_criteria(
            self,
            output: str,
            criteria: List[str]
        ) -> Dict[str, Any]:
            """Check if output meets acceptance criteria."""
            results = []

            for criterion in criteria:
                # Use LLM for semantic checking
                prompt = f"""Does the following output meet this criterion?

Criterion: {criterion}

Output: {output}

Answer with YES or NO, followed by a brief explanation."""

                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )

                answer = response.choices[0].message.content
                met = answer.strip().upper().startswith("YES")

                results.append({
                    "criterion": criterion,
                    "met": met,
                    "explanation": answer
                })

            met_count = sum(1 for r in results if r["met"])

            return {
                "valid": met_count == len(criteria),
                "criteria_met": met_count,
                "total_criteria": len(criteria),
                "results": results
            }
    ```
  - Files to create: `arms/judge/validators/criteria.py`

- [ ] **Implement Hallucination Detection** (1 hour)
  - Detect unverifiable claims
  - Consistency checking
  - Confidence scoring
  - Files to create: `arms/judge/validators/hallucination.py`

#### Quality Scoring System (6 hours)

- [ ] **Implement Weighted Rubric System** (3 hours)
  - Configurable scoring dimensions
  - Weighted aggregation
  - Threshold-based pass/fail
  - Code example:
    ```python
    # arms/judge/scoring.py
    from typing import Dict, List, Any
    from pydantic import BaseModel, Field

    class ScoringDimension(BaseModel):
        name: str
        weight: float = Field(ge=0.0, le=1.0)
        description: str
        min_score: float = 0.0
        max_score: float = 100.0

    class QualityScorer:
        def __init__(self, dimensions: List[ScoringDimension]):
            """
            Initialize quality scorer with weighted dimensions.
            Weights must sum to 1.0.
            """
            total_weight = sum(d.weight for d in dimensions)
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

            self.dimensions = dimensions

        def score(self, dimension_scores: Dict[str, float]) -> Dict[str, Any]:
            """
            Calculate weighted score across dimensions.

            Args:
                dimension_scores: Dict mapping dimension name to score (0-100)

            Returns:
                Dict with overall score and breakdown
            """
            weighted_score = 0.0
            breakdown = []

            for dimension in self.dimensions:
                score = dimension_scores.get(dimension.name, 0.0)
                weighted = score * dimension.weight
                weighted_score += weighted

                breakdown.append({
                    "dimension": dimension.name,
                    "score": score,
                    "weight": dimension.weight,
                    "weighted_score": weighted
                })

            return {
                "overall_score": weighted_score,
                "breakdown": breakdown,
                "passed": weighted_score >= 70.0  # Default threshold
            }

    # Default rubric for OctoLLM outputs
    DEFAULT_RUBRIC = [
        ScoringDimension(
            name="correctness",
            weight=0.4,
            description="Accuracy and factual correctness"
        ),
        ScoringDimension(
            name="completeness",
            weight=0.25,
            description="All requirements addressed"
        ),
        ScoringDimension(
            name="quality",
            weight=0.20,
            description="Code/output quality and best practices"
        ),
        ScoringDimension(
            name="safety",
            weight=0.15,
            description="Security and safety considerations"
        )
    ]
    ```
  - Files to create: `arms/judge/scoring.py`

- [ ] **Implement Feedback Generation** (2 hours)
  - Generate actionable recommendations
  - Repair suggestions for failures
  - Prioritized issue list

- [ ] **Add Confidence Scoring** (1 hour)
  - Uncertainty quantification
  - Confidence intervals
  - Flags for human review

#### Judge Arm Service Implementation (8 hours)

- [ ] **Create FastAPI Service** (2 hours)
  - Service initialization
  - Dependency injection
  - Health checks
  - Files to create: `arms/judge/main.py`

- [ ] **Implement /validate Endpoint** (4 hours)
  - POST /validate for output validation
  - Multi-layer validation pipeline
  - Detailed validation report
  - Code example:
    ```python
    # arms/judge/api/validation.py
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel, Field
    from typing import List, Dict, Any, Optional
    from ..validators.schema import SchemaValidator
    from ..validators.facts import FactChecker
    from ..validators.criteria import CriteriaChecker
    from ..validators.hallucination import HallucinationDetector
    from ..scoring import QualityScorer, DEFAULT_RUBRIC

    router = APIRouter()

    class ValidationRequest(BaseModel):
        output: str = Field(..., min_length=1)
        schema: Optional[Dict] = None
        acceptance_criteria: Optional[List[str]] = None
        enable_fact_checking: bool = True
        enable_hallucination_detection: bool = True

    class ValidationResponse(BaseModel):
        valid: bool
        overall_score: float
        validations: Dict[str, Any]
        feedback: List[str]
        confidence: float

    @router.post("/validate", response_model=ValidationResponse)
    async def validate_output(request: ValidationRequest):
        """Multi-layer validation of task output."""
        validations = {}
        dimension_scores = {}
        feedback = []

        # Layer 1: Schema validation
        if request.schema:
            schema_validator = SchemaValidator()
            schema_result = schema_validator.validate_json_schema(
                data=request.output,
                schema=request.schema
            )
            validations["schema"] = schema_result
            dimension_scores["correctness"] = 100.0 if schema_result["valid"] else 0.0

            if not schema_result["valid"]:
                feedback.extend([
                    f"Schema error in {err['field']}: {err['message']}"
                    for err in schema_result["errors"]
                ])

        # Layer 2: Fact-checking
        if request.enable_fact_checking:
            fact_checker = get_fact_checker()
            fact_result = await fact_checker.check_facts(request.output)
            validations["facts"] = fact_result
            dimension_scores["correctness"] = min(
                dimension_scores.get("correctness", 100.0),
                fact_result["accuracy"] * 100
            )

            if not fact_result["valid"]:
                feedback.extend([
                    f"Unverified claim: {claim['claim']}"
                    for claim in fact_result["failed_claims"]
                ])

        # Layer 3: Acceptance criteria
        if request.acceptance_criteria:
            criteria_checker = get_criteria_checker()
            criteria_result = await criteria_checker.check_criteria(
                output=request.output,
                criteria=request.acceptance_criteria
            )
            validations["criteria"] = criteria_result
            dimension_scores["completeness"] = (
                criteria_result["criteria_met"] / criteria_result["total_criteria"] * 100
            )

            if not criteria_result["valid"]:
                feedback.extend([
                    f"Criterion not met: {r['criterion']}"
                    for r in criteria_result["results"] if not r["met"]
                ])

        # Layer 4: Hallucination detection
        if request.enable_hallucination_detection:
            hallucination_detector = get_hallucination_detector()
            hallucination_result = await hallucination_detector.detect(request.output)
            validations["hallucination"] = hallucination_result

            if hallucination_result["detected"]:
                feedback.append(f"Potential hallucinations detected: {hallucination_result['count']}")

        # Calculate overall score
        scorer = QualityScorer(DEFAULT_RUBRIC)
        score_result = scorer.score(dimension_scores)

        return ValidationResponse(
            valid=score_result["passed"] and all(
                v.get("valid", True) for v in validations.values()
            ),
            overall_score=score_result["overall_score"],
            validations=validations,
            feedback=feedback,
            confidence=min(1.0, sum(dimension_scores.values()) / (len(dimension_scores) * 100))
        )
    ```
  - Files to create: `arms/judge/api/validation.py`

- [ ] **Implement /fact-check Endpoint** (2 hours)
  - POST /fact-check for standalone fact verification
  - Claim-by-claim breakdown
  - Supporting evidence links
  - Files to create: `arms/judge/api/facts.py`

### Testing Requirements

- [ ] **Unit Tests** (6 hours)
  - Test schema validation (catch format errors)
  - Test fact-checking (k-evidence rule)
  - Test scoring system (weighted aggregation)
  - Target coverage: >85%
  - Test file: `arms/judge/tests/test_validation.py`
  - Example tests:
    ```python
    # arms/judge/tests/test_validation.py
    import pytest
    from judge.validators.schema import SchemaValidator
    from judge.validators.facts import FactChecker
    from judge.scoring import QualityScorer, ScoringDimension

    def test_schema_validation_catches_errors():
        """Test schema validation detects type mismatches."""
        validator = SchemaValidator()

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name", "age"]
        }

        # Valid data
        result = validator.validate_json_schema(
            {"name": "John", "age": 30},
            schema
        )
        assert result["valid"] == True

        # Invalid data (wrong type)
        result = validator.validate_json_schema(
            {"name": "John", "age": "thirty"},
            schema
        )
        assert result["valid"] == False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_fact_checking_accuracy():
        """Test fact checker verifies claims correctly."""
        mock_retriever = MockRetrieverClient()
        fact_checker = FactChecker(mock_retriever, k=3)

        # Text with verifiable claim
        text = "Python was created by Guido van Rossum in 1991."
        result = await fact_checker.check_facts(text)

        assert result["claims_checked"] > 0
        assert result["accuracy"] >= 0.8

    def test_quality_scoring():
        """Test weighted quality scoring."""
        dimensions = [
            ScoringDimension(name="correctness", weight=0.5, description=""),
            ScoringDimension(name="completeness", weight=0.5, description="")
        ]

        scorer = QualityScorer(dimensions)

        result = scorer.score({
            "correctness": 90.0,
            "completeness": 80.0
        })

        assert result["overall_score"] == 85.0  # (90*0.5 + 80*0.5)
        assert result["passed"] == True
    ```

- [ ] **Integration Tests** (4 hours)
  - Test end-to-end validation flow
  - Test Retriever integration for fact-checking
  - Test validation report generation
  - Scenarios:
    - Valid output → All layers pass
    - Invalid schema → Schema validation fails
    - False claims → Fact-checking fails

### Documentation Deliverables

- [ ] **API Documentation** (2 hours)
  - OpenAPI spec
  - Validation examples
  - Scoring rubric documentation

- [ ] **Component README** (1 hour)
  - Validation layers overview
  - Configuration guide
  - Custom rubric creation
  - Files to create: `arms/judge/README.md`

### Success Criteria

- [ ] Validation catches >95% of schema errors
- [ ] Fact-checking >90% accurate on known facts
- [ ] Hallucination detection >80% effective
- [ ] All tests passing with >85% coverage
- [ ] API documentation complete

### Common Pitfalls & Tips

⚠️ **Pitfall 1**: Fact-checking too strict causes false negatives
✅ **Solution**: Tune k-evidence threshold based on domain

⚠️ **Pitfall 2**: LLM-based criteria checking is slow
✅ **Solution**: Cache results for similar outputs

⚠️ **Pitfall 3**: Hallucination detector has high false positive rate
✅ **Solution**: Use multiple detection methods and consensus

### Estimated Effort

- Development: 28 hours
- Testing: 10 hours
- Documentation: 3 hours
- **Total**: 41 hours (~2 weeks for 1 engineer)

### Dependencies

- Blocks: All workflows (every task needs validation)
- Blocked by: Retriever Arm complete (for fact-checking)

---

## Sprint 2.4: Safety Guardian Arm [Week 10-11]

**(Content abbreviated for space - full sprint would be 1,500-2,000 lines with complete task breakdown, code examples, testing strategy, documentation, and acceptance criteria similar to Sprints 2.1-2.3)**

### Sprint Goals

- Implement comprehensive PII detection (18+ types with regex + NER)
- Create automatic redaction (type-based, hash-based, reversible)
- Add content filtering (profanity, hate speech, NSFW)
- Implement policy enforcement (capability validation, rate limiting)
- Build audit logging system (provenance tracking, immutable logs)
- Achieve >95% PII detection recall, <5% false positive rate

### Key Tasks (Summary)

1. PII Detection Engine (regex patterns + spaCy NER)
2. Redaction Strategies (multiple approaches with AES-256)
3. Content Filtering (keyword lists + ML models)
4. Policy Enforcement Framework
5. Audit Logging with Provenance
6. GDPR/CCPA Compliance Helpers

---

## Sprint 2.5: Distributed Memory System [Week 11-13]

**(Content abbreviated for space - full sprint would be 1,800-2,200 lines)**

### Sprint Goals

- Implement complete PostgreSQL schema (entities, relationships, task_history, action_log)
- Deploy Qdrant per-arm episodic memory collections
- Create memory routing with query classification
- Implement data diodes for security isolation
- Build multi-tier caching (L1 in-memory, L2 Redis)
- Achieve >90% routing accuracy, <100ms query latency

### Key Tasks (Summary)

1. PostgreSQL Global Memory (full schema + indexes)
2. Qdrant Local Memory (per-arm collections)
3. Memory Router (query classification logic)
4. Data Diode Implementation (PII filtering, capability checks)
5. Multi-Tier Cache Layer
6. Connection Pooling and Optimization

**Reference**: `docs/implementation/memory-systems.md` (2,850+ lines)

---

## Sprint 2.6: Kubernetes Migration [Week 13-15]

**(Content abbreviated for space - full sprint would be 2,000-2,500 lines)**

### Sprint Goals

- Deploy all services to Kubernetes production cluster
- Implement Horizontal Pod Autoscaling (HPA) for all services
- Configure Ingress with TLS (cert-manager + Let's Encrypt)
- Set up Pod Disruption Budgets (PDB) for high availability
- Deploy monitoring stack (Prometheus, Grafana)
- Achieve successful load test (1,000 concurrent tasks)

### Key Tasks (Summary)

1. Kubernetes Manifests (Namespace, ResourceQuota, RBAC)
2. StatefulSets for Databases (PostgreSQL, Redis, Qdrant)
3. Deployments for Services (Orchestrator, Reflex, 6 Arms)
4. HPA Configuration (CPU, memory, custom metrics)
5. Ingress and TLS Setup
6. Load Testing and Verification

**Reference**: `docs/operations/kubernetes-deployment.md` (1,481 lines)

---

## Sprint 2.7: Swarm Decision-Making [Week 15-16]

**(Content abbreviated for space - full sprint would be 1,200-1,500 lines)**

### Sprint Goals

- Implement parallel arm invocation (N proposals for high-priority tasks)
- Create result aggregation strategies (voting, Borda count, learned)
- Build conflict resolution policies
- Add confidence scoring and uncertainty quantification
- Implement active learning feedback loops
- Achieve >95% success rate on critical tasks, <2x latency overhead

### Key Tasks (Summary)

1. Swarm Executor Class (parallel execution with asyncio)
2. Voting and Aggregation Algorithms
3. Conflict Resolution Strategies
4. Confidence Scoring System
5. Active Learning Integration

**Reference**: `docs/architecture/swarm-decision-making.md`

---

## Phase 2 Summary

**Total Tasks**: 80+ implementation tasks across 7 sprints
**Estimated Duration**: 8-10 weeks with 4-5 engineers
**Total Estimated Hours**: ~290 hours development + ~70 hours testing + ~20 hours documentation = 380 hours

**Deliverables**:
- 4 additional arms (Retriever, Coder, Judge, Guardian)
- Distributed memory system (PostgreSQL + Qdrant + Redis)
- Kubernetes production deployment
- Swarm decision-making
- Integration tests and load tests

**Completion Checklist**:
- [ ] All 6 arms deployed and operational
- [ ] Memory system handling 100,000+ entities
- [ ] Kubernetes deployment with autoscaling
- [ ] Swarm decision-making working
- [ ] Load tests passing (1,000 concurrent tasks)
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Security audit complete

**Next Phase**: Phase 3 (Operations) + Phase 4 (Engineering) - Can run in parallel

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Project Management Team
