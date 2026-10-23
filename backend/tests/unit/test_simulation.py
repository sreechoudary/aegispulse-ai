"""Simulation engine tests (Req 1.*)."""
import pytest

from app.contracts import FIXED_OPTION_SET
from app.simulation import InvalidScenarioError, SimulationEngine

E = SimulationEngine()

def test_five_scenarios_registered():
    assert len(E.list_scenarios()) == 5

def test_bad_deployment_deterministic_and_wellformed():
    a = E.generate("Bad_Deployment", 42)
    b = E.generate("Bad_Deployment", 42)
    assert a == b  # byte-for-byte equal structure
    for name, s in a["series"].items():
        assert len(s) >= 1 and all(v >= 0 for v in s)

def test_different_seed_differs():
    assert E.generate("Bad_Deployment", 1) != E.generate("Bad_Deployment", 2)

def test_invalid_scenario_rejected():
    with pytest.raises(InvalidScenarioError) as ei:
        E.generate("Kaiju_Attack", 1)
    assert ei.value.scenario_id == "Kaiju_Attack"

def test_execute_state_changing_restores():
    out = E.execute("rollback_deployment", {"incident": "i1"})
    assert out.result == "success" and out.service_impact == "restored" and out.mttr_seconds > 0

def test_execute_non_state_changing_is_noop():
    out = E.execute("investigate_further", {})
    assert out.service_impact == "no-op" and out.mttr_seconds == 0.0

def test_execute_rejects_unknown_tool():
    with pytest.raises(ValueError):
        E.execute("delete_everything", {})

def test_expected_outcomes_are_in_option_set():
    for spec in E.list_scenarios():
        assert spec.expected_outcome in FIXED_OPTION_SET
