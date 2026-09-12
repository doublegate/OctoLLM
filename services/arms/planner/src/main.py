"""
Planner arm — stub.

No implementation yet; this exists so the image serves something real instead
of crash-looping, and so `docker compose up` can reach a healthy state. The
/execute endpoint returns 501 rather than a plausible fake, so an unimplemented
arm is never mistaken for a working one. Stage 8 builds the real thing.
"""

from octollm_stub import create_stub_app

app = create_stub_app(
    arm_id="planner",
    name="Planner",
    description="Decomposes a goal into a dependency-ordered plan of arm calls.",
    port=8001,
    capabilities=["task_planning", "goal_decomposition"],
    implemented_in_stage=8,
)
