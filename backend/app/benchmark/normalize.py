"""
Normalized incident evidence (fairness fix from the methodology audit).

The original benchmark fed the Decider a terse metric summary while giving Bedrock a
task-framed prompt — not comparable inputs. This builds ONE normalized evidence
description (metrics + plain-language signals) that BOTH arms receive identically, so
Evaluation A is an equal-context comparison. The signals are derived deterministically
from the telemetry (no model, no labels leaked).
"""
from __future__ import annotations

from typing import Any


def normalized_evidence(telemetry: dict[str, Any]) -> str:
    s = telemetry["series"]
    err0, err1 = s["error_rate_pct"][0], s["error_rate_pct"][-1]
    lat0, lat1 = s["latency_p95_ms"][0], s["latency_p95_ms"][-1]
    cpu = s["cpu_pct"][-1]; mem0, mem1 = s["memory_pct"][0], s["memory_pct"][-1]
    db = s["db_connections_pct"][-1]
    signals = []
    if err1 > err0 * 3 and err1 > 5:
        signals.append("HTTP 5xx error rate spiked sharply")
    if cpu > 80:
        signals.append("CPU is saturated")
    if lat1 > 300:
        signals.append("p95 latency is elevated")
    if mem1 > mem0 + 20:
        signals.append("memory is growing steadily (possible leak)")
    if db > 80:
        signals.append("database connections are near the limit")
    if not signals:
        signals.append("signals are mild, mixed, or inconclusive")
    return (
        f"Incident telemetry: error_rate {err0}%->{err1}%, p95_latency {lat0}ms->{lat1}ms, "
        f"cpu {cpu}%, memory {mem0}%->{mem1}%, db_connections {db}%. "
        f"Observed signals: {'; '.join(signals)}."
    )
