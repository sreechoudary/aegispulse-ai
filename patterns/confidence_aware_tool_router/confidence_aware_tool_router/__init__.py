"""Confidence-Aware Recovery Tool Router — reusable #tool-selection pattern."""
from .core import (
    ConfidenceAwareToolRouter, ToolChoiceDecision, DeciderDecision,
    DEFAULT_RECOVERY_TOOLS, OutOfSetError, MalformedResponseError, DeciderUnavailableError,
)
from .intervention import map_to_action, build_intervention_handler

__all__ = [
    "ConfidenceAwareToolRouter", "ToolChoiceDecision", "DeciderDecision",
    "DEFAULT_RECOVERY_TOOLS", "OutOfSetError", "MalformedResponseError",
    "DeciderUnavailableError", "map_to_action", "build_intervention_handler",
]
__version__ = "0.1.0"
