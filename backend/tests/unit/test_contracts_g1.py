"""
G1 contract self-check. Proves the frozen contracts import cleanly and their
validation invariants fire. Run: pytest backend/tests/unit/test_contracts_g1.py
"""
import pytest
from pydantic import ValidationError

from app.contracts import (
    ALLOWED_TRANSITIONS,
    ALWAYS_APPROVE_TOOLS,
    BLAST_RADIUS,
    FIXED_OPTION_SET,
    STATE_CHANGING_TOOLS,
    BlastRadius,
    DeciderDecision,
    DeciderRawResponse,
    EventEnvelope,
    EventType,
    IncidentState,
    PolicyInput,
)


def test_fixed_option_set_is_five_tools():
    assert FIXED_OPTION_SET == (
        "rollback_deployment", "scale_out_service", "restart_unhealthy_tasks",
        "investigate_further", "escalate_to_human")


def test_blast_radius_covers_every_tool():
    assert set(BLAST_RADIUS) == set(FIXED_OPTION_SET)
    assert BLAST_RADIUS["rollback_deployment"] is BlastRadius.HIGH
    assert BLAST_RADIUS["restart_unhealthy_tasks"] is BlastRadius.MEDIUM


def test_always_approve_are_high_blast_state_changing():
    for t in ALWAYS_APPROVE_TOOLS:
        assert BLAST_RADIUS[t] is BlastRadius.HIGH
        assert t in STATE_CHANGING_TOOLS


def test_decider_decision_rejects_out_of_set():
    with pytest.raises(ValidationError):
        DeciderDecision(selected="reboot_universe", confidence=0.9, scores={},
                        model_version="m", latency_ms=1.0, evidence_snapshot_id="e")


def test_decider_decision_rejects_confidence_out_of_bounds():
    with pytest.raises(ValidationError):
        DeciderDecision(selected="rollback_deployment", confidence=1.5, scores={},
                        model_version="m", latency_ms=1.0, evidence_snapshot_id="e")


def test_decider_decision_accepts_valid():
    d = DeciderDecision(selected="rollback_deployment", confidence=0.95,
                        scores={"rollback_deployment": 0.95}, model_version="m",
                        latency_ms=199.0, evidence_snapshot_id="e1")
    assert d.selected == "rollback_deployment"


def test_raw_response_parses_real_m0_shape():
    raw = DeciderRawResponse(
        model="strands-decider-2B-qwen3.5-v1-2610",
        answers={"recovery_tool": {"type": "choice", "choice": "rollback_deployment",
                 "probabilities": {"rollback_deployment": 0.96}, "confidence": 0.955}},
        usage={"input_tokens": 199, "output_tokens": 1}, latency_ms=199.31)
    assert raw.answers["recovery_tool"].choice == "rollback_deployment"


def test_transition_table_rollback_path_and_rejects_illegal():
    assert IncidentState.EXECUTING.value in ALLOWED_TRANSITIONS[IncidentState.AUTO_AUTHORIZED.value]
    # illegal: cannot jump Created -> Executing
    assert IncidentState.EXECUTING.value not in ALLOWED_TRANSITIONS[IncidentState.CREATED.value]


def test_policy_input_is_bedrock_free():
    inp = PolicyInput(candidate_tool="rollback_deployment", confidence=0.95,
                      evidence_present=True)
    # no field can carry Bedrock text
    assert "bedrock" not in " ".join(inp.model_dump().keys()).lower()


def test_event_envelope_roundtrip():
    e = EventEnvelope(event_id="evt1", correlation_id="cid1", incident_id="inc1",
                      timestamp="2026-10-18T00:00:00.000Z", type=EventType.DECIDER_DECISION,
                      payload={"selected": "rollback_deployment"})
    assert EventEnvelope.model_validate(e.model_dump()).type is EventType.DECIDER_DECISION
