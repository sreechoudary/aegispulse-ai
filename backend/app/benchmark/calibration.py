"""
Calibration metrics (Phase 3 decision quality): Brier score and Expected Calibration
Error (ECE). For a multi-class decision, we use the confidence assigned to the SELECTED
option and whether that selection was correct (a standard top-label calibration view).
"""
from __future__ import annotations


def brier_score(confidences: list[float], corrects: list[bool]) -> float | None:
    """Mean squared error between confidence-in-selected and correctness indicator."""
    if not confidences:
        return None
    n = len(confidences)
    return round(sum((c - (1.0 if ok else 0.0)) ** 2 for c, ok in zip(confidences, corrects)) / n, 4)


def expected_calibration_error(confidences: list[float], corrects: list[bool],
                               bins: int = 10) -> float | None:
    """ECE: weighted average gap between confidence and accuracy across confidence bins."""
    if not confidences:
        return None
    n = len(confidences)
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for c, ok in zip(confidences, corrects):
        idx = min(bins - 1, int(c * bins))
        buckets[idx].append((c, ok))
    ece = 0.0
    for b in buckets:
        if not b:
            continue
        avg_conf = sum(c for c, _ in b) / len(b)
        acc = sum(1 for _, ok in b if ok) / len(b)
        ece += (len(b) / n) * abs(avg_conf - acc)
    return round(ece, 4)
