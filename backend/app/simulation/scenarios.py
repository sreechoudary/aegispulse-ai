"""
Scenario registry with labeled expected outcomes.

Expected outcomes are TEST EXPECTATIONS sourced independently of any Decider response
(Req 1.7). They are NOT fed to the Decider and never hard-code its answer.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.contracts import RecoveryTool, ScenarioId


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    name: str
    description: str
    expected_outcome: str  # labeled expectation, independent of Decider
    context_signal: str = ""  # deterministic contextual FACT (not the answer) for the Decider state


SCENARIOS: dict[str, ScenarioSpec] = {
    ScenarioId.BAD_DEPLOYMENT.value: ScenarioSpec(
        ScenarioId.BAD_DEPLOYMENT.value, "Bad Deployment",
        "A new release causes a sharp increase in HTTP 5xx errors.",
        RecoveryTool.ROLLBACK_DEPLOYMENT.value,
        context_signal="a new deployment completed 8 minutes ago"),
    ScenarioId.CAPACITY_SATURATION.value: ScenarioSpec(
        ScenarioId.CAPACITY_SATURATION.value, "Capacity Saturation",
        "CPU and request-queue saturation increase latency.",
        RecoveryTool.SCALE_OUT_SERVICE.value,
        context_signal="traffic volume is elevated with no recent deployment"),
    ScenarioId.MEMORY_LEAK.value: ScenarioSpec(
        ScenarioId.MEMORY_LEAK.value, "Memory Leak",
        "Repeated memory growth and unhealthy tasks.",
        RecoveryTool.RESTART_UNHEALTHY_TASKS.value,
        context_signal="memory has grown steadily over hours; some tasks are unhealthy"),
    ScenarioId.DATABASE_CONNECTION_EXHAUSTION.value: ScenarioSpec(
        ScenarioId.DATABASE_CONNECTION_EXHAUSTION.value, "Database Connection Exhaustion",
        "Database connections approach the limit; a blind restart is unsafe.",
        RecoveryTool.INVESTIGATE_FURTHER.value,
        context_signal="database connection pool is near its limit; cause not yet confirmed"),
    ScenarioId.AMBIGUOUS_INCIDENT.value: ScenarioSpec(
        ScenarioId.AMBIGUOUS_INCIDENT.value, "Ambiguous Incident",
        "Incomplete or contradictory telemetry.",
        RecoveryTool.ESCALATE_TO_HUMAN.value,
        context_signal="signals are contradictory and no single root cause is evident"),
}
