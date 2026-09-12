"""
Retriever arm — stub.

No implementation yet; this exists so the image serves something real instead
of crash-looping, and so `docker compose up` can reach a healthy state. The
/execute endpoint returns 501 rather than a plausible fake, so an unimplemented
arm is never mistaken for a working one. Stage 8 builds the real thing.
"""

from octollm_stub import create_stub_app

app = create_stub_app(
    arm_id="retriever",
    name="Retriever",
    description="Ranks candidates with BM25, vector search and reciprocal-rank fusion. Memory owns storage.",
    port=8002,
    capabilities=["search", "ranking", "rank_fusion"],
    implemented_in_stage=8,
)
