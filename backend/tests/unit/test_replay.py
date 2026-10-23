"""Replay / Incident Time Machine tests (Req 7)."""
import pytest
from app.replay import (validate_conditions, apply_conditions, compare,
                        InvalidReplayConditionsError)
from app.simulation import SimulationEngine

E = SimulationEngine()


def test_invalid_conditions_rejected():
    with pytest.raises(InvalidReplayConditionsError):
        validate_conditions({})
    with pytest.raises(InvalidReplayConditionsError):
        validate_conditions({"bogus_key": 1})
    with pytest.raises(InvalidReplayConditionsError):
        validate_conditions({"error_rate_multiplier": -1})


def test_valid_conditions_accepted():
    validate_conditions({"error_rate_multiplier": 0.1})
    validate_conditions({"inject_db_pressure": True})


def test_apply_conditions_deterministic_and_transforms():
    base = E.generate("Bad_Deployment", 42)
    a = apply_conditions(base, {"error_rate_multiplier": 0.0})
    b = apply_conditions(base, {"error_rate_multiplier": 0.0})
    assert a == b  # deterministic
    assert all(v == 0.0 for v in a["series"]["error_rate_pct"])  # zeroed errors
    assert base["series"]["error_rate_pct"][-1] > 0  # original untouched


def test_apply_does_not_mutate_original():
    base = E.generate("Bad_Deployment", 42)
    snapshot = base["series"]["error_rate_pct"][:]
    apply_conditions(base, {"error_rate_multiplier": 5.0})
    assert base["series"]["error_rate_pct"] == snapshot  # original record unchanged


def test_compare_detects_change_and_no_change():
    orig = {"selected": "rollback_deployment", "confidence": 0.79, "policy_outcome": "PendingApproval"}
    same = dict(orig)
    cmp_same = compare(orig, same, "i1", "i2", {"error_rate_multiplier": 1.0})
    assert not cmp_same.tool_changed
    assert all(not d.changed for d in cmp_same.diffs)

    diff = {"selected": "investigate_further", "confidence": 0.4, "policy_outcome": "AutoAuthorized"}
    cmp_diff = compare(orig, diff, "i1", "i3", {"error_rate_multiplier": 0.05})
    assert cmp_diff.tool_changed
    assert cmp_diff.original_label == "REAL Decider inference"
    assert cmp_diff.outcome_label == "SIMULATED recovery outcome"
