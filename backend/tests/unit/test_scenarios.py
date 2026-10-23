"""Phase 4: each scenario has distinct, characteristic, deterministic telemetry."""
from app.simulation import SimulationEngine

E = SimulationEngine()


def _last(t, metric):
    return t["series"][metric][-1]


def test_bad_deployment_shows_error_spike():
    t = E.generate("Bad_Deployment", 42)
    assert _last(t, "error_rate_pct") > 5.0  # 5xx spike
    assert t["service_health"] == "degraded"


def test_capacity_saturation_shows_cpu_and_latency():
    t = E.generate("Capacity_Saturation", 42)
    assert _last(t, "cpu_pct") > 80.0
    assert _last(t, "latency_p95_ms") > 300.0


def test_memory_leak_shows_memory_growth():
    t = E.generate("Memory_Leak", 42)
    assert _last(t, "memory_pct") > t["series"]["memory_pct"][0] + 20


def test_db_exhaustion_shows_high_db_connections():
    t = E.generate("Database_Connection_Exhaustion", 42)
    assert _last(t, "db_connections_pct") > 80.0


def test_ambiguous_incident_is_milder():
    t = E.generate("Ambiguous_Incident", 42)
    # ambiguous: no single dominant signal
    assert _last(t, "error_rate_pct") < 10.0


def test_all_scenarios_distinct_summaries():
    sums = {s.scenario_id: E.generate(s.scenario_id, 7)["summary"] for s in E.list_scenarios()}
    assert len(set(sums.values())) == 5  # all distinct


def test_labeled_outcomes_match_design_intent():
    expected = {s.scenario_id: s.expected_outcome for s in E.list_scenarios()}
    assert expected["Bad_Deployment"] == "rollback_deployment"
    assert expected["Capacity_Saturation"] == "scale_out_service"
    assert expected["Memory_Leak"] == "restart_unhealthy_tasks"
    assert expected["Database_Connection_Exhaustion"] == "investigate_further"
    assert expected["Ambiguous_Incident"] == "escalate_to_human"
