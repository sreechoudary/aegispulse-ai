"""
Property-based tests for AegisPulse deterministic core (Hypothesis, >=100 iters each).
Each test is tagged with its design Property number.
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from app.contracts import (
    ALWAYS_APPROVE_TOOLS,
    FIXED_OPTION_SET,
    STATE_CHANGING_TOOLS,
    ApprovalStatus,
    DeciderHealth,
    PolicyInput,
    PolicyOutcome,
)
from app.policy import PolicyEngine
from app.simulation import SimulationEngine

E = SimulationEngine()
P = PolicyEngine()
SCENARIOS = [s.scenario_id for s in E.list_scenarios()]
SEED = st.integers(min_value=0, max_value=4_294_967_295)
TOOL = st.sampled_from(list(FIXED_OPTION_SET))
CONF = st.floats(min_value=0.0, max_value=1.0)


# Feature: chaospilot-ai, Property 1: Telemetry well-formedness invariant
@settings(max_examples=120)
@given(st.sampled_from(SCENARIOS), SEED)
def test_property1_telemetry_wellformed(scenario, seed):
    t = E.generate(scenario, seed)
    for series in t["series"].values():
        assert len(series) >= 1
        assert all(v >= 0 for v in series)


# Feature: chaospilot-ai, Property 2: Deterministic telemetry reproduction
@settings(max_examples=120)
@given(st.sampled_from(SCENARIOS), SEED)
def test_property2_deterministic(scenario, seed):
    assert E.generate(scenario, seed) == E.generate(scenario, seed)


# Feature: chaospilot-ai, Property 18: High-blast-radius tools always require approval
@settings(max_examples=120)
@given(CONF)
def test_property18_high_blast_never_auto(conf):
    for tool in ALWAYS_APPROVE_TOOLS:
        d = P.authorize(PolicyInput(candidate_tool=tool, confidence=conf,
                        evidence_present=True, approval_status=ApprovalStatus.NONE))
        assert d.outcome is PolicyOutcome.PENDING_APPROVAL
        assert not d.may_execute


# Feature: chaospilot-ai, Property 17: Confidence gate applies to automatic state-changing only
@settings(max_examples=120)
@given(CONF)
def test_property17_threshold_gates_medium_blast(conf):
    d = P.authorize(PolicyInput(candidate_tool="restart_unhealthy_tasks", confidence=conf,
                    evidence_present=True))
    if conf < 0.90:
        assert d.outcome is PolicyOutcome.BLOCKED
    else:
        assert d.outcome is PolicyOutcome.AUTO_AUTHORIZED
    # non-state-changing always permitted regardless of confidence
    inv = P.authorize(PolicyInput(candidate_tool="investigate_further", confidence=conf,
                      evidence_present=True))
    assert inv.outcome is PolicyOutcome.AUTO_AUTHORIZED


# Feature: chaospilot-ai, Property 13: Fail closed on Decider failure for state-changing
@settings(max_examples=120)
@given(TOOL, CONF, st.sampled_from([DeciderHealth.OUT_OF_SET, DeciderHealth.MALFORMED,
                                    DeciderHealth.UNAVAILABLE]))
def test_property13_fail_closed(tool, conf, health):
    d = P.authorize(PolicyInput(candidate_tool=tool, confidence=conf, evidence_present=True,
                    decider_health=health))
    if tool in STATE_CHANGING_TOOLS:
        assert d.outcome is PolicyOutcome.FAILED_CLOSED
        assert not d.may_execute
    else:
        assert d.may_execute is False  # permitted but nothing to execute


# Feature: chaospilot-ai, Property 15: Only allowlisted tools are authorized
@settings(max_examples=120)
@given(st.text(min_size=1, max_size=20), CONF)
def test_property15_allowlist(tool, conf):
    d = P.authorize(PolicyInput(candidate_tool=tool, confidence=conf, evidence_present=True))
    if tool not in FIXED_OPTION_SET:
        assert d.outcome is PolicyOutcome.BLOCKED
