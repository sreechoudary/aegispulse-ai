"""
Optional Strands intervention helper for the #tool-selection pattern.

Maps a (DeciderDecision, policy_outcome) pair to a Strands intervention action.
The pure `map_to_action` function holds the logic and is unit-testable without
constructing a real Strands lifecycle event.

Verified against strands-agents 1.61.1 (M0): actions live in `strands.interventions`
(Proceed, Deny, Confirm, Guide, Transform); InterventionHandler.before_tool_call
receives a typed BeforeToolCallEvent. See README limitations for deltas.
"""
from __future__ import annotations
from typing import Callable, Any

from .core import DeciderDecision, DEFAULT_RECOVERY_TOOLS

# Tools that are high-blast-radius and must always route to human confirmation.
HIGH_BLAST_RADIUS: frozenset[str] = frozenset({"rollback_deployment", "scale_out_service"})
NON_STATE_CHANGING: frozenset[str] = frozenset({"investigate_further", "escalate_to_human"})


def map_to_action(decision: DeciderDecision, policy_outcome: str) -> str:
    """Pure mapping returning one of: Proceed | Deny | Confirm | Guide.

    policy_outcome is one of: AutoAuthorized | PendingApproval | Blocked | FailedClosed.
    This is deterministic and depends ONLY on the Decider selection + the policy
    outcome — never on any Bedrock/LLM text.
    """
    if policy_outcome in ("Blocked", "FailedClosed"):
        return "Deny"
    if decision.selected in HIGH_BLAST_RADIUS or policy_outcome == "PendingApproval":
        return "Confirm"
    if decision.selected == "investigate_further":
        return "Guide"
    if policy_outcome == "AutoAuthorized":
        return "Proceed"
    return "Deny"  # safe default (fail closed)


def build_intervention_handler(router: Any, policy: Callable[[DeciderDecision], str]) -> Any:
    """Build a Strands InterventionHandler whose before_tool_call composes the
    Decider selection with the injected policy callable. `policy` takes a
    DeciderDecision and returns a policy_outcome string.

    Imports Strands lazily so the rest of the package is usable without the SDK
    installed (e.g. in environments that only parse decisions).
    """
    from strands import InterventionHandler  # type: ignore
    from strands.interventions import Proceed, Deny, Confirm, Guide  # type: ignore

    _ACTIONS = {"Proceed": Proceed, "Deny": Deny, "Confirm": Confirm, "Guide": Guide}

    class _RecoveryInterventionHandler(InterventionHandler):  # type: ignore[misc]
        @property
        def name(self) -> str:
            return "confidence_aware_recovery_tool_router"

        def before_tool_call(self, event, **kwargs):  # noqa: ANN001
            decision = getattr(event, "aegis_decision", None)
            if decision is None:
                return Proceed()
            outcome = policy(decision)
            action_name = map_to_action(decision, outcome)
            return _ACTIONS[action_name]()

    return _RecoveryInterventionHandler()
