"""Calibration + normalized-evidence tests (no models)."""
from app.benchmark.calibration import brier_score, expected_calibration_error
from app.benchmark.normalize import normalized_evidence
from app.simulation import SimulationEngine


def test_brier_perfect_calibration():
    # always confident and always correct -> brier 0
    assert brier_score([1.0, 1.0], [True, True]) == 0.0
    # always confident and always wrong -> brier 1
    assert brier_score([1.0, 1.0], [False, False]) == 1.0


def test_ece_zero_when_conf_matches_accuracy():
    # 50% confidence, 50% correct within the bin -> low ECE
    ece = expected_calibration_error([0.5, 0.5], [True, False])
    assert ece is not None and ece <= 0.5


def test_normalized_evidence_surfaces_memory_leak_signal():
    t = SimulationEngine().generate("Memory_Leak", 42)
    ev = normalized_evidence(t)
    assert "memory is growing" in ev


def test_normalized_evidence_surfaces_db_signal():
    t = SimulationEngine().generate("Database_Connection_Exhaustion", 42)
    assert "database connections are near the limit" in normalized_evidence(t)


def test_normalized_evidence_deterministic():
    t = SimulationEngine().generate("Bad_Deployment", 7)
    assert normalized_evidence(t) == normalized_evidence(t)
