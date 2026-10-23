"""
Deterministic incident Simulation Engine.

- Seeded, reproducible telemetry (Req 1.2, 1.3).
- Simulation-only remediation; holds NO AWS client and mutates no real resource
  (Req 1.4, 1.8, 6.18).
- Invalid scenarios rejected with a structured error (Req 1.6).
"""
from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.contracts import FIXED_OPTION_SET

from .scenarios import SCENARIOS, ScenarioSpec


class InvalidScenarioError(ValueError):
    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id
        super().__init__(f"unknown scenario id {scenario_id!r}")


@dataclass(frozen=True)
class RecoveryOutcome:
    tool: str
    mttr_seconds: float
    service_impact: str
    result: str  # "success" | "failure"


class SimulationEngine:
    """Deterministic generator + simulation-only executor. No AWS mutation client."""

    def list_scenarios(self) -> list[ScenarioSpec]:
        return list(SCENARIOS.values())

    def expected_outcome(self, scenario_id: str) -> str:
        self._require(scenario_id)
        return SCENARIOS[scenario_id].expected_outcome

    def _require(self, scenario_id: str) -> ScenarioSpec:
        spec = SCENARIOS.get(scenario_id)
        if spec is None:
            raise InvalidScenarioError(scenario_id)
        return spec

    def generate(self, scenario_id: str, seed: int) -> dict[str, Any]:
        """Deterministic telemetry. Same (scenario, seed) -> identical output."""
        self._require(scenario_id)
        if not (0 <= seed <= 4_294_967_295):
            raise ValueError("seed out of uint32 range")
        rng = random.Random(f"{scenario_id}:{seed}")
        n = 12  # time series points
        profile = self._profile(scenario_id)
        series = {
            "error_rate_pct": [round(max(0.0, profile["err_base"] + profile["err_slope"] * i
                                         + rng.uniform(0, profile["err_jitter"])), 3) for i in range(n)],
            "latency_p95_ms": [round(max(0.0, profile["lat_base"] + profile["lat_slope"] * i
                                         + rng.uniform(0, profile["lat_jitter"])), 1) for i in range(n)],
            "cpu_pct": [round(max(0.0, min(100.0, profile["cpu_base"] + profile["cpu_slope"] * i
                                           + rng.uniform(0, 3))), 1) for i in range(n)],
            "memory_pct": [round(max(0.0, min(100.0, profile["mem_base"] + profile["mem_slope"] * i
                                              + rng.uniform(0, 2))), 1) for i in range(n)],
            "db_connections_pct": [round(max(0.0, min(100.0, profile["db_base"] + profile["db_slope"] * i
                                                      + rng.uniform(0, 2))), 1) for i in range(n)],
        }
        health = "degraded" if (series["error_rate_pct"][-1] > 5 or series["latency_p95_ms"][-1] > 400
                                or series["cpu_pct"][-1] > 85) else "healthy"
        return {
            "scenario_id": scenario_id,
            "seed": seed,
            "service_health": health,
            "series": series,
            "context_signal": SCENARIOS[scenario_id].context_signal,
            "summary": self._summary(scenario_id, series),
            "topology": self._topology(scenario_id, series, health),
        }


    def _topology(self, scenario_id: str, series: dict, health: str) -> dict:
        """Deterministic SIMULATED service graph for the scenario, with node status derived
        from the generated telemetry (not invented). Illustrative of the simulated
        environment only; this is not real AWS resource discovery."""
        last = {k: v[-1] for k, v in series.items()}
        def status(flag):
            return "critical" if flag else "ok"
        nodes = [
            {"id": "alb", "label": "Load Balancer", "kind": "alb",
             "status": status(last["error_rate_pct"] > 5 or last["latency_p95_ms"] > 400),
             "metric": f"5xx {last['error_rate_pct']}% · p95 {last['latency_p95_ms']}ms"},
            {"id": "svc", "label": "App Service", "kind": "service",
             "status": status(last["cpu_pct"] > 85 or last["error_rate_pct"] > 5),
             "metric": f"cpu {last['cpu_pct']}%"},
            {"id": "tasks", "label": "Tasks / Pods", "kind": "compute",
             "status": status(last["memory_pct"] > 85),
             "metric": f"mem {last['memory_pct']}%"},
            {"id": "db", "label": "Database", "kind": "database",
             "status": status(last["db_connections_pct"] > 80),
             "metric": f"connections {last['db_connections_pct']}%"},
            {"id": "deploy", "label": "Latest Deployment", "kind": "deployment",
             "status": status(scenario_id == "Bad_Deployment"),
             "metric": SCENARIOS[scenario_id].context_signal or "no recent change"},
        ]
        edges = [
            {"from": "deploy", "to": "svc"},
            {"from": "alb", "to": "svc"},
            {"from": "svc", "to": "tasks"},
            {"from": "svc", "to": "db"},
        ]
        return {"nodes": nodes, "edges": edges, "overall": health}

    def execute(self, tool: str, params: Mapping[str, Any]) -> RecoveryOutcome:
        """Simulation-only. Deterministic outcome keyed by tool+params; no real effect."""
        if tool not in FIXED_OPTION_SET:
            raise ValueError(f"tool {tool!r} not allowlisted")
        digest = hashlib.sha256(
            (tool + json.dumps(dict(params), sort_keys=True)).encode()).hexdigest()
        # deterministic pseudo-outcome; state-changing tools "restore", others are no-ops
        state_changing = tool in {"rollback_deployment", "scale_out_service", "restart_unhealthy_tasks"}
        mttr = 20.0 + (int(digest[:4], 16) % 60)  # 20..79s, deterministic
        if not state_changing:
            return RecoveryOutcome(tool=tool, mttr_seconds=0.0, service_impact="no-op", result="success")
        return RecoveryOutcome(tool=tool, mttr_seconds=float(mttr),
                               service_impact="restored", result="success")

    def _profile(self, scenario_id: str) -> dict[str, float]:
        base = {"err_base": 0.2, "err_slope": 0.0, "err_jitter": 0.1,
                "lat_base": 180.0, "lat_slope": 0.0, "lat_jitter": 10,
                "cpu_base": 40.0, "cpu_slope": 0.0, "mem_base": 45.0, "mem_slope": 0.0,
                "db_base": 30.0, "db_slope": 0.0}
        if scenario_id == "Bad_Deployment":
            base.update(err_base=0.2, err_slope=1.3, err_jitter=0.5, lat_slope=6)
        elif scenario_id == "Capacity_Saturation":
            base.update(cpu_base=55, cpu_slope=3.5, lat_slope=22, lat_jitter=20)
        elif scenario_id == "Memory_Leak":
            base.update(mem_base=50, mem_slope=3.8, err_slope=0.3)
        elif scenario_id == "Database_Connection_Exhaustion":
            base.update(db_base=60, db_slope=3.2, err_slope=0.6, lat_slope=8)
        elif scenario_id == "Ambiguous_Incident":
            base.update(err_slope=0.4, lat_slope=4, cpu_slope=1.0, mem_slope=0.8)
        return base

    def _summary(self, scenario_id: str, series: dict) -> str:
        return (f"scenario={scenario_id} "
                f"err {series['error_rate_pct'][0]}->{series['error_rate_pct'][-1]}% "
                f"p95 {series['latency_p95_ms'][0]}->{series['latency_p95_ms'][-1]}ms "
                f"cpu->{series['cpu_pct'][-1]}% mem->{series['memory_pct'][-1]}% "
                f"db->{series['db_connections_pct'][-1]}%")
