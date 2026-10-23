"""
AegisPulse AI — FROZEN shared enums and error codes (G1 Interface Freeze).

SINGLE SOURCE OF TRUTH. Do not redefine these values anywhere else in the codebase.
Any change requires Lead Architect approval and a G1 re-freeze.

Grounded in M0 validation (2026-10-18): real Strands Decider serve contract and
strands-agents 1.61.1 InterventionHandler actions.
"""
from __future__ import annotations

from enum import Enum


class RecoveryTool(str, Enum):
    """The fixed option set presented to the Decider (Req 3.1). Order is stable."""
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    SCALE_OUT_SERVICE = "scale_out_service"
    RESTART_UNHEALTHY_TASKS = "restart_unhealthy_tasks"
    INVESTIGATE_FURTHER = "investigate_further"
    ESCALATE_TO_HUMAN = "escalate_to_human"


# Canonical tuple used BOTH for Decider request construction and response validation.
FIXED_OPTION_SET: tuple[str, ...] = tuple(t.value for t in RecoveryTool)

# State-changing tools are the only ones gated by the confidence threshold (Req 6.4-6.6).
STATE_CHANGING_TOOLS: frozenset[str] = frozenset({
    RecoveryTool.ROLLBACK_DEPLOYMENT.value,
    RecoveryTool.SCALE_OUT_SERVICE.value,
    RecoveryTool.RESTART_UNHEALTHY_TASKS.value,
})


class BlastRadius(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    NONE = "none"


# Frozen blast-radius classification (design: Safety Policy Engine table, Req 6.7-6.8).
BLAST_RADIUS: dict[str, BlastRadius] = {
    RecoveryTool.ROLLBACK_DEPLOYMENT.value: BlastRadius.HIGH,
    RecoveryTool.SCALE_OUT_SERVICE.value: BlastRadius.HIGH,
    RecoveryTool.RESTART_UNHEALTHY_TASKS.value: BlastRadius.MEDIUM,
    RecoveryTool.INVESTIGATE_FURTHER.value: BlastRadius.NONE,
    RecoveryTool.ESCALATE_TO_HUMAN.value: BlastRadius.NONE,
}

# Tools that ALWAYS require human approval regardless of confidence (Req 6.7).
ALWAYS_APPROVE_TOOLS: frozenset[str] = frozenset({
    RecoveryTool.ROLLBACK_DEPLOYMENT.value,
    RecoveryTool.SCALE_OUT_SERVICE.value,
})

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.90  # configurable; default per Req 6.4 / calibration
DEFAULT_APPROVAL_EXPIRY_SECONDS: int = 120   # configurable (Req 6.10)
DECIDER_TIMEOUT_SECONDS: float = 10.0        # Req 3.10
MAX_FAILED_ATTEMPTS: int = 3                 # Req 6.16


class ScenarioId(str, Enum):
    BAD_DEPLOYMENT = "Bad_Deployment"
    CAPACITY_SATURATION = "Capacity_Saturation"
    MEMORY_LEAK = "Memory_Leak"
    DATABASE_CONNECTION_EXHAUSTION = "Database_Connection_Exhaustion"
    AMBIGUOUS_INCIDENT = "Ambiguous_Incident"


class IncidentState(str, Enum):
    """Server-validated incident lifecycle states (design: Incident State Machine)."""
    CREATED = "Created"
    SIMULATING = "Simulating"
    INVESTIGATING = "Investigating"
    ASSESSING = "Assessing"
    DECIDING = "Deciding"
    POLICY_EVALUATED = "PolicyEvaluated"
    AUTO_AUTHORIZED = "AutoAuthorized"
    PENDING_APPROVAL = "PendingApproval"
    BLOCKED = "Blocked"
    FAILED_CLOSED = "FailedClosed"
    EXECUTING = "Executing"
    RECOVERED = "Recovered"
    RECOVERY_FAILED = "RecoveryFailed"
    REPLAYING = "Replaying"


# Frozen allowed transitions (design: Incident State Machine). Server rejects others (Req 10.6).
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    IncidentState.CREATED.value: frozenset({IncidentState.SIMULATING.value}),
    IncidentState.SIMULATING.value: frozenset({IncidentState.INVESTIGATING.value}),
    IncidentState.INVESTIGATING.value: frozenset({IncidentState.ASSESSING.value}),
    IncidentState.ASSESSING.value: frozenset({IncidentState.DECIDING.value}),
    IncidentState.DECIDING.value: frozenset({
        IncidentState.POLICY_EVALUATED.value, IncidentState.FAILED_CLOSED.value}),
    IncidentState.POLICY_EVALUATED.value: frozenset({
        IncidentState.AUTO_AUTHORIZED.value, IncidentState.PENDING_APPROVAL.value,
        IncidentState.BLOCKED.value}),
    IncidentState.PENDING_APPROVAL.value: frozenset({
        IncidentState.AUTO_AUTHORIZED.value, IncidentState.BLOCKED.value}),
    IncidentState.AUTO_AUTHORIZED.value: frozenset({IncidentState.EXECUTING.value}),
    IncidentState.EXECUTING.value: frozenset({
        IncidentState.RECOVERED.value, IncidentState.RECOVERY_FAILED.value}),
    IncidentState.RECOVERY_FAILED.value: frozenset({IncidentState.BLOCKED.value}),
    IncidentState.RECOVERED.value: frozenset({IncidentState.REPLAYING.value}),
    IncidentState.BLOCKED.value: frozenset({IncidentState.REPLAYING.value}),
    IncidentState.FAILED_CLOSED.value: frozenset({IncidentState.REPLAYING.value}),
    IncidentState.REPLAYING.value: frozenset({IncidentState.DECIDING.value}),
}


class PolicyOutcome(str, Enum):
    AUTO_AUTHORIZED = "AutoAuthorized"
    PENDING_APPROVAL = "PendingApproval"
    BLOCKED = "Blocked"
    FAILED_CLOSED = "FailedClosed"


class ApprovalStatus(str, Enum):
    NONE = "none"
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DeciderHealth(str, Enum):
    HEALTHY = "healthy"
    OUT_OF_SET = "out_of_set"
    MALFORMED = "malformed"
    UNAVAILABLE = "unavailable"


class InterventionAction(str, Enum):
    """Maps to strands-agents 1.61.1 actions. NOTE (M0 finding): Transform exists
    beyond Proceed/Deny/Confirm/Guide; before_tool_call receives a typed
    BeforeToolCallEvent, not loose args."""
    PROCEED = "Proceed"
    DENY = "Deny"
    CONFIRM = "Confirm"
    GUIDE = "Guide"
    TRANSFORM = "Transform"


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    FAIL_CLOSED = "FAIL_CLOSED"
    APPROVAL_INVALID = "APPROVAL_INVALID"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"


class EventType(str, Enum):
    TELEMETRY_GENERATED = "telemetry_generated"
    TOOL_INVOKED = "tool_invoked"
    TOOL_ERROR = "tool_error"
    EVIDENCE_SNAPSHOT_CREATED = "evidence_snapshot_created"
    BEDROCK_ASSESSMENT = "bedrock_assessment"
    DECIDER_DECISION = "decider_decision"
    DECIDER_ERROR = "decider_error"
    POLICY_EVALUATED = "policy_evaluated"
    ACTION_DENIED = "action_denied"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    ACTION_EXECUTED = "action_executed"
    RECOVERY_MEASURED = "recovery_measured"
    REPLAY_STARTED = "replay_started"
    REPLAY_COMPARED = "replay_compared"
    BENCHMARK_STARTED = "benchmark_started"
    BENCHMARK_COMPLETED = "benchmark_completed"
    HEARTBEAT = "heartbeat"
    SECURITY_EVENT = "security_event"
