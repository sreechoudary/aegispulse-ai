"""
Incident Time Machine — counterfactual replay (Phase 3, Req 7).

Re-runs a completed incident with modified conditions through the REAL Decider, then
compares original vs replayed decision/confidence/policy field-by-field. Labels Decider
predictions as REAL inference and recovery outcomes as SIMULATED. Never mutates the
original incident record (replay creates a new incident id).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDiff:
    field: str
    original: Any
    replayed: Any
    changed: bool


@dataclass(frozen=True)
class ReplayComparison:
    original_incident_id: str
    replay_incident_id: str
    modified_conditions: dict[str, Any]
    diffs: list[FieldDiff]
    original_label: str = "REAL Decider inference"
    outcome_label: str = "SIMULATED recovery outcome"

    @property
    def tool_changed(self) -> bool:
        return any(d.field == "selected" and d.changed for d in self.diffs)


VALID_CONDITION_KEYS = {"error_rate_multiplier", "latency_multiplier", "seed_override",
                        "inject_db_pressure", "inject_memory_growth"}


class InvalidReplayConditionsError(ValueError):
    pass


def validate_conditions(conditions: dict[str, Any]) -> None:
    if not isinstance(conditions, dict) or not conditions:
        raise InvalidReplayConditionsError("conditions must be a non-empty object")
    unknown = set(conditions) - VALID_CONDITION_KEYS
    if unknown:
        raise InvalidReplayConditionsError(f"unknown condition keys: {sorted(unknown)}")
    for k in ("error_rate_multiplier", "latency_multiplier"):
        if k in conditions and (not isinstance(conditions[k], (int, float)) or conditions[k] < 0):
            raise InvalidReplayConditionsError(f"{k} must be a non-negative number")


def apply_conditions(telemetry: dict[str, Any], conditions: dict[str, Any]) -> dict[str, Any]:
    """Deterministically transform telemetry per the modified conditions."""
    t = copy.deepcopy(telemetry)
    s = t["series"]
    if "error_rate_multiplier" in conditions:
        s["error_rate_pct"] = [round(v * conditions["error_rate_multiplier"], 3) for v in s["error_rate_pct"]]
    if "latency_multiplier" in conditions:
        s["latency_p95_ms"] = [round(v * conditions["latency_multiplier"], 1) for v in s["latency_p95_ms"]]
    if conditions.get("inject_db_pressure"):
        s["db_connections_pct"] = [min(100.0, v + 55) for v in s["db_connections_pct"]]
    if conditions.get("inject_memory_growth"):
        s["memory_pct"] = [min(100.0, v + 45) for v in s["memory_pct"]]
    t["summary"] = (f"scenario={t['scenario_id']} (replay) "
                    f"err {s['error_rate_pct'][0]}->{s['error_rate_pct'][-1]}% "
                    f"p95 {s['latency_p95_ms'][0]}->{s['latency_p95_ms'][-1]}ms "
                    f"cpu->{s['cpu_pct'][-1]}% mem->{s['memory_pct'][-1]}% db->{s['db_connections_pct'][-1]}%")
    return t


def compare(original: dict[str, Any], replayed: dict[str, Any],
            original_incident_id: str, replay_incident_id: str,
            conditions: dict[str, Any]) -> ReplayComparison:
    """Field-level diff of selected tool, confidence, policy outcome."""
    diffs = []
    for field in ("selected", "confidence", "policy_outcome"):
        o, r = original.get(field), replayed.get(field)
        diffs.append(FieldDiff(field=field, original=o, replayed=r, changed=(o != r)))
    return ReplayComparison(original_incident_id=original_incident_id,
                            replay_incident_id=replay_incident_id,
                            modified_conditions=conditions, diffs=diffs)
