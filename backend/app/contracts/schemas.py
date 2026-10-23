"""
AegisPulse AI — FROZEN shared schemas (G1 Interface Freeze).

SINGLE SOURCE OF TRUTH for cross-component data contracts. Pydantic v2 models with
explicit typing and validation. Any change requires Lead Architect approval.

Decider request/response shapes are the REAL serve contract verified in M0
(docs/validation/sample_request.json / sample_response.json).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import (
    FIXED_OPTION_SET,
    ApprovalStatus,
    BlastRadius,
    DeciderHealth,
    ErrorCode,
    EventType,
    PolicyOutcome,
)

# ---------- Decider serve contract (REAL /v1/systemone shape) ----------

class DeciderChoiceQuestion(BaseModel):
    """One question in the serve request `questions` keyed object (type=choice)."""
    model_config = ConfigDict(frozen=True)
    type: str = Field(default="choice")
    instructions: str
    criteria: dict[str, str]  # option_name -> description (improves selection; M0 finding)


class DeciderRequest(BaseModel):
    """POST /v1/systemone body. `questions` is a KEYED OBJECT, not an array."""
    state: str
    questions: dict[str, DeciderChoiceQuestion]


class DeciderChoiceAnswer(BaseModel):
    """One answer in the serve response `answers` keyed object."""
    type: str
    choice: str
    probabilities: dict[str, float]
    confidence: float


class DeciderRawResponse(BaseModel):
    """Verbatim serve response: answers keyed object + top-level model/usage/latency_ms."""
    model: str
    answers: dict[str, DeciderChoiceAnswer]
    usage: dict[str, int]
    latency_ms: float


class DeciderDecision(BaseModel):
    """Normalized internal representation (adapter output). Fields map FROM the raw
    response: selected<-choice, scores<-probabilities, model<-model, latency_ms<-latency_ms."""
    model_config = ConfigDict(frozen=True)
    selected: str
    confidence: float
    scores: dict[str, float]
    model_version: str
    latency_ms: float
    evidence_snapshot_id: str

    @field_validator("selected")
    @classmethod
    def _in_set(cls, v: str) -> str:
        if v not in FIXED_OPTION_SET:
            raise ValueError(f"selected tool {v!r} not in fixed option set")
        return v

    @field_validator("confidence")
    @classmethod
    def _bounded(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence {v} out of [0,1]")
        return v


# ---------- Evidence & decision records ----------

class EvidenceSnapshot(BaseModel):
    """Immutable capture of incident state + evidence refs submitted to the Decider."""
    model_config = ConfigDict(frozen=True)
    evidence_snapshot_id: str
    incident_id: str
    correlation_id: str
    created_at: str  # ISO-8601 ms
    telemetry_summary: dict[str, Any]
    evidence_refs: list[str]


class DecisionRecord(BaseModel):
    """Immutable record capturing the full context + outcome of one decision (Req 11.1)."""
    model_config = ConfigDict(frozen=True)
    decision_record_id: str
    incident_id: str
    correlation_id: str
    evidence_snapshot_id: str
    input_state: dict[str, Any]
    evidence_references: list[str]
    typed_question: dict[str, Any]
    available_options: list[str]
    selected_option: str
    confidence: float
    per_option_scores: dict[str, float]
    model_version: str
    inference_latency_ms: float
    policy_outcome: PolicyOutcome
    approval_status: ApprovalStatus
    execution_result: dict[str, Any] | None = None


# ---------- Policy authorize() contract ----------

class PolicyInput(BaseModel):
    """Deterministic inputs to authorize(). NEVER contains Bedrock text (Req 5.6)."""
    model_config = ConfigDict(frozen=True)
    candidate_tool: str
    confidence: float
    evidence_present: bool
    approval_status: ApprovalStatus = ApprovalStatus.NONE
    attempt_count: int = 0
    decider_health: DeciderHealth = DeciderHealth.HEALTHY
    confidence_threshold: float = 0.90


class PolicyDecision(BaseModel):
    """authorize() output."""
    model_config = ConfigDict(frozen=True)
    outcome: PolicyOutcome
    reason: str
    blast_radius: BlastRadius
    requires_approval: bool
    may_execute: bool


# ---------- Approval binding ----------

class ApprovalBinding(BaseModel):
    """Exact-match tuple an approval is bound to (Req 6.9)."""
    model_config = ConfigDict(frozen=True)
    incident_id: str
    action: str
    action_parameters: dict[str, Any]
    evidence_snapshot_id: str


# ---------- Event envelope ----------

class EventEnvelope(BaseModel):
    """SSE/event-store envelope. `event_id` is a monotonic ULID used as SSE id."""
    model_config = ConfigDict(frozen=True)
    event_id: str
    correlation_id: str
    incident_id: str
    timestamp: str  # ISO-8601 ms
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------- API error envelope ----------

class ApiError(BaseModel):
    code: ErrorCode
    message: str
    field: str | None = None
    correlation_id: str


class ApiErrorResponse(BaseModel):
    error: ApiError
