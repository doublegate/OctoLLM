"""
Safety Guardian arm.

Not implemented yet: `POST /check` returns 501 naming the stage that builds it,
rather than a plausible fake. A stub that answered convincingly would make an
unimplemented arm indistinguishable from a working one.

Everything specific to this arm lives elsewhere on purpose:

  * its declaration is one entry in `octollm_common.roster`, which the orchestrator's
    registry and `scripts/ci/check_port_map.py` read from the same place;
  * its request and response models come from `octollm_common.models.contracts`,
    which the orchestrator imports as its client models -- so a field rename here is
    a type error there rather than a 422 discovered in production.

What remains is the wiring, and there is deliberately nothing else to get wrong.
"""

from octollm_common import create_arm_app
from octollm_common.models.contracts import CheckRequest, CheckResponse
from octollm_common.roster import spec_for

SPEC = spec_for("safety-guardian")

app = create_arm_app(SPEC, request_model=CheckRequest, response_model=CheckResponse)
