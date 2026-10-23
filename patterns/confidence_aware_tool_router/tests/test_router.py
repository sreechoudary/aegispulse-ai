"""Unit tests for the reusable tool router. No real Decider — fake transport."""
import pytest
from confidence_aware_tool_router import (
    ConfidenceAwareToolRouter, ToolChoiceDecision, DEFAULT_RECOVERY_TOOLS,
    OutOfSetError, MalformedResponseError, DeciderUnavailableError, map_to_action, DeciderDecision,
)
from confidence_aware_tool_router.core import _Transport, DeciderUnavailableError as CoreUnavail


DECISION = ToolChoiceDecision(
    question_id="recovery_tool",
    options=DEFAULT_RECOVERY_TOOLS,
    prompt="Select the single best recovery tool.",
    criteria={t: t.replace("_", " ") for t in DEFAULT_RECOVERY_TOOLS},
)


class FakeTransport(_Transport):
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
    def post_json(self, url, body, timeout_s):
        if self._exc:
            raise self._exc
        return self._response


def _resp(choice="rollback_deployment", confidence=0.95):
    return {"model": "strands-decider-2B-qwen3.5-v1-2610",
            "answers": {"recovery_tool": {"type": "choice", "choice": choice,
                        "probabilities": {choice: confidence}, "confidence": confidence}},
            "usage": {"input_tokens": 100, "output_tokens": 1}, "latency_ms": 199.0}


def test_happy_path_in_set():
    r = ConfidenceAwareToolRouter("http://x", transport=FakeTransport(_resp()))
    d = r.decide("state", DECISION, "ev1")
    assert d.selected == "rollback_deployment"
    assert 0.0 <= d.confidence <= 1.0
    assert d.evidence_snapshot_id == "ev1"


def test_out_of_set_raises():
    r = ConfidenceAwareToolRouter("http://x", transport=FakeTransport(_resp(choice="reboot_universe")))
    with pytest.raises(OutOfSetError) as ei:
        r.decide("state", DECISION, "ev1")
    assert ei.value.returned_value == "reboot_universe"


def test_missing_choice_raises_malformed():
    bad = _resp()
    del bad["answers"]["recovery_tool"]["choice"]
    r = ConfidenceAwareToolRouter("http://x", transport=FakeTransport(bad))
    with pytest.raises(MalformedResponseError):
        r.decide("state", DECISION, "ev1")


def test_confidence_out_of_bounds_raises_malformed():
    r = ConfidenceAwareToolRouter("http://x", transport=FakeTransport(_resp(confidence=1.5)))
    with pytest.raises(MalformedResponseError):
        r.decide("state", DECISION, "ev1")


def test_unavailable_raises():
    r = ConfidenceAwareToolRouter("http://x", transport=FakeTransport(exc=CoreUnavail("boom")))
    with pytest.raises(DeciderUnavailableError):
        r.decide("state", DECISION, "ev1")


def test_build_request_shape():
    r = ConfidenceAwareToolRouter("http://x")
    body = r.build_request("some state", DECISION)
    assert set(body) == {"state", "questions"}
    q = body["questions"]["recovery_tool"]
    assert q["type"] == "choice"
    assert set(q["criteria"]) == set(DEFAULT_RECOVERY_TOOLS)


# --- intervention mapping (task 3.4) ---
def _dec(tool):
    return DeciderDecision(selected=tool, confidence=0.95, scores={tool: 0.95},
                           model="m", latency_ms=1.0, evidence_snapshot_id="e")

def test_map_high_blast_radius_to_confirm():
    assert map_to_action(_dec("rollback_deployment"), "PendingApproval") == "Confirm"
    assert map_to_action(_dec("scale_out_service"), "PendingApproval") == "Confirm"

def test_map_blocked_to_deny():
    assert map_to_action(_dec("restart_unhealthy_tasks"), "Blocked") == "Deny"
    assert map_to_action(_dec("rollback_deployment"), "FailedClosed") == "Deny"

def test_map_auto_authorized_to_proceed():
    assert map_to_action(_dec("restart_unhealthy_tasks"), "AutoAuthorized") == "Proceed"

def test_map_investigate_to_guide():
    assert map_to_action(_dec("investigate_further"), "AutoAuthorized") == "Guide"
