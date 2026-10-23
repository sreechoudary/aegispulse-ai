"""
AegisPulse backend Decider adapter.

The ONLY place where the reusable package types meet the frozen G1 app contracts.
Consumes confidence_aware_tool_router and produces app.contracts.DeciderDecision,
mapping the package exceptions to the contracts exception types.
"""
from __future__ import annotations

from confidence_aware_tool_router import (
    ConfidenceAwareToolRouter,
    ToolChoiceDecision,
)
from confidence_aware_tool_router.core import (
    DeciderUnavailableError as PkgUnavailable,
)
from confidence_aware_tool_router.core import (
    MalformedResponseError as PkgMalformed,
)
from confidence_aware_tool_router.core import (
    OutOfSetError as PkgOutOfSet,
)

from app.contracts import (
    DECIDER_TIMEOUT_SECONDS,
    FIXED_OPTION_SET,
    DeciderUnavailableError,
    MalformedResponseError,
    OutOfSetError,
)
from app.contracts import (
    DeciderDecision as ContractDecision,
)

RECOVERY_QUESTION_ID = "recovery_tool"
_CRITERIA = {
    "rollback_deployment": "Use ONLY when errors spiked right after a new deployment",
    "scale_out_service": "Use ONLY when CPU or request queue is saturated from high load",
    "restart_unhealthy_tasks": "Use ONLY when memory grows over time indicating a leak in tasks",
    "investigate_further": "Use when the cause is a resource limit like database connections where acting blindly is unsafe",
    "escalate_to_human": "Use when telemetry is contradictory or no single cause is clear",
}


class DeciderAdapter:
    """Wraps the reusable router and returns frozen-contract DeciderDecision objects."""

    def __init__(self, endpoint: str, router: ConfidenceAwareToolRouter | None = None) -> None:
        self._router = router or ConfidenceAwareToolRouter(
            endpoint, timeout_s=DECIDER_TIMEOUT_SECONDS)
        self._decision = ToolChoiceDecision(
            question_id=RECOVERY_QUESTION_ID,
            options=FIXED_OPTION_SET,
            prompt="Select the single best recovery tool for this incident.",
            criteria=_CRITERIA,
        )

    def decide(self, state: str, evidence_snapshot_id: str, correlation_id: str = "") -> ContractDecision:
        try:
            d = self._router.decide(state, self._decision, evidence_snapshot_id)
        except PkgOutOfSet as e:
            raise OutOfSetError(e.returned_value, correlation_id) from e
        except PkgMalformed as e:
            raise MalformedResponseError(str(e)) from e
        except PkgUnavailable as e:
            raise DeciderUnavailableError(str(e)) from e
        return ContractDecision(
            selected=d.selected,
            confidence=d.confidence,
            scores=d.scores,
            model_version=d.model,
            latency_ms=d.latency_ms,
            evidence_snapshot_id=d.evidence_snapshot_id,
        )
