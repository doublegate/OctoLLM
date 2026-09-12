"""
Shared framework for the eight arms and the orchestrator.

The single-definition seam: `models.contracts` holds every arm's request and response
models, imported by the arms as their FastAPI models and by the orchestrator as its
client models. There is no second definition to drift from.

This replaces `octollm_stub`, which existed only so the arm images could come up
healthy in Stage 3.
"""

from .app import ArmSpec, create_arm_app
from .errors import error_body, install_error_handlers

__all__ = ["ArmSpec", "create_arm_app", "error_body", "install_error_handlers"]
