"""
Shared framework for the eight arms and the orchestrator.

The single-definition seam: `models.contracts` holds every arm's request and response
models, imported by the arms as their FastAPI models and by the orchestrator as its
client models. There is no second definition to drift from.

This replaces `octollm_stub`, which existed only so the arm images could come up
healthy in Stage 3.

Stage 5 adds the Neural Ring and its authorization: `capability` mints and checks the
grants, `ring` carries artifacts on Redis Streams within declared topology, `peer`
makes the direct arm-to-arm calls the tight loops need, and `security` is the callee's
enforcement point. `ring` and `peer` are not re-exported here -- they pull in redis and
httpx transports that a service using only the contracts has no reason to import.
"""

from .app import ArmSpec, create_arm_app
from .capability import (
    CapabilityClaims,
    CapabilityConfigError,
    CapabilityDenied,
    CapabilityIssuer,
    CapabilityVerifier,
    InMemoryCallCounter,
    PeerConstraints,
    RedisCallCounter,
)
from .errors import error_body, install_error_handlers
from .security import CapabilityPolicy, RequireCapability

__all__ = [
    "ArmSpec",
    "CapabilityClaims",
    "CapabilityConfigError",
    "CapabilityDenied",
    "CapabilityIssuer",
    "CapabilityPolicy",
    "CapabilityVerifier",
    "InMemoryCallCounter",
    "PeerConstraints",
    "RedisCallCounter",
    "RequireCapability",
    "create_arm_app",
    "error_body",
    "install_error_handlers",
]
