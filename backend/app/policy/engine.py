"""
Deterministic Safety Policy Engine (Req 6, 16.6/16.7).

Pure function of PolicyInput. NEVER reads Bedrock/LLM text (Req 5.6). Evaluation order
puts blast radius BEFORE the confidence gate so high-blast-radius tools always route to
approval, even at confidence 1.0 (resolves Req 16.6 vs 6.7).
"""
from __future__ import annotations

from app.contracts import (
    ALWAYS_APPROVE_TOOLS,
    BLAST_RADIUS,
    FIXED_OPTION_SET,
    MAX_FAILED_ATTEMPTS,
    STATE_CHANGING_TOOLS,
    ApprovalStatus,
    BlastRadius,
    DeciderHealth,
    PolicyDecision,
    PolicyInput,
    PolicyOutcome,
)


class PolicyEngine:
    """Sole authorizer. Deterministic and side-effect free."""

    def authorize(self, inp: PolicyInput) -> PolicyDecision:
        tool = inp.candidate_tool
        blast = BLAST_RADIUS.get(tool, BlastRadius.NONE)

        # 0. Fail closed on any Decider failure for state-changing actions (Req 6.14).
        if inp.decider_health is not DeciderHealth.HEALTHY:
            if tool in STATE_CHANGING_TOOLS:
                return self._d(PolicyOutcome.FAILED_CLOSED, "decider-unhealthy-fail-closed", blast, False, False)
            # read-only investigate/escalate still permitted
            return self._d(PolicyOutcome.AUTO_AUTHORIZED, "decider-unhealthy-readonly-permitted", blast, False, False)

        # 1. Allowlist (Req 6.1).
        if tool not in FIXED_OPTION_SET:
            return self._d(PolicyOutcome.BLOCKED, "non-allowlisted", blast, False, False)

        # 2. Non-state-changing tools: always permitted, nothing to execute.
        if tool not in STATE_CHANGING_TOOLS:
            return self._d(PolicyOutcome.AUTO_AUTHORIZED, "non-state-changing", blast, False, False)

        # 3. Missing evidence blocks state-changing (Req 6.3).
        if not inp.evidence_present:
            return self._d(PolicyOutcome.BLOCKED, "missing-evidence", blast, False, False)

        # 4. Retry limit (Req 6.16).
        if inp.attempt_count >= MAX_FAILED_ATTEMPTS:
            return self._d(PolicyOutcome.BLOCKED, "retry-limit-exceeded", blast, False, False)

        # 5. Blast radius BEFORE confidence (Req 6.7/6.8 vs 16.6): high-blast always approve.
        if tool in ALWAYS_APPROVE_TOOLS:
            if inp.approval_status is ApprovalStatus.APPROVED:
                return self._d(PolicyOutcome.AUTO_AUTHORIZED, "approved-high-blast", blast, True, True)
            if inp.approval_status in (ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED):
                return self._d(PolicyOutcome.BLOCKED, f"approval-{inp.approval_status.value}", blast, True, False)
            return self._d(PolicyOutcome.PENDING_APPROVAL, "high-blast-radius-requires-approval", blast, True, False)

        # 6. Medium blast (restart): confidence gate applies (Req 6.4-6.6).
        if inp.confidence < inp.confidence_threshold:
            return self._d(PolicyOutcome.BLOCKED, "below-threshold", blast, False, False)
        return self._d(PolicyOutcome.AUTO_AUTHORIZED, "medium-blast-above-threshold", blast, False, True)

    @staticmethod
    def _d(outcome, reason, blast, requires_approval, may_execute):
        return PolicyDecision(outcome=outcome, reason=reason, blast_radius=blast,
                              requires_approval=requires_approval, may_execute=may_execute)
