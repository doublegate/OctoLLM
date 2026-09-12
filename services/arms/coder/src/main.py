"""
Coder arm — stub.

No implementation yet; this exists so the image serves something real instead
of crash-looping, and so `docker compose up` can reach a healthy state. The
/execute endpoint returns 501 rather than a plausible fake, so an unimplemented
arm is never mistaken for a working one. Stage 8 builds the real thing.
"""

from octollm_stub import create_stub_app

app = create_stub_app(
    arm_id="coder",
    name="Coder",
    description="Generates, debugs, refactors and explains code.",
    port=8003,
    capabilities=["code_generation", "debugging", "refactoring"],
    implemented_in_stage=8,
)
