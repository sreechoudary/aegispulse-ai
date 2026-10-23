"""QA: evaluation dataset integrity + contract conformance (no fabricated measurements)."""
import json
import pathlib

from app.contracts import FIXED_OPTION_SET, ScenarioId

EVAL = pathlib.Path(__file__).resolve().parents[3] / "evaluation" / "eval_cases.json"


def test_eval_dataset_has_at_least_50_cases():
    data = json.loads(EVAL.read_text())
    assert data["count"] >= 50
    assert len(data["cases"]) >= 50


def test_eval_cases_cover_all_five_scenarios_min_five_each():
    data = json.loads(EVAL.read_text())
    counts = {}
    valid_scenarios = {s.value for s in ScenarioId}
    for c in data["cases"]:
        assert c["scenario_id"] in valid_scenarios
        assert c["expected_recovery_tool"] in FIXED_OPTION_SET
        assert 0 <= c["seed"] <= 4_294_967_295
        counts[c["scenario_id"]] = counts.get(c["scenario_id"], 0) + 1
    assert set(counts) == valid_scenarios
    assert all(v >= 5 for v in counts.values())


def test_eval_case_ids_unique():
    data = json.loads(EVAL.read_text())
    ids = [c["case_id"] for c in data["cases"]]
    assert len(ids) == len(set(ids))


def test_labels_independent_of_decider():
    # Guard: the dataset must document that labels are not Decider outputs.
    data = json.loads(EVAL.read_text())
    assert "independent" in data["label_policy"].lower()
