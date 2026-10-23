"""
Benchmark Lab (Phase 5, Req 8).

Compares REAL Decider 2B tool selection against a Bedrock-only baseline on identical
inputs + fixed option set. Warms up both systems; records steady-state measurements only.
Never fabricates results — every number is measured from a real call. Discloses hardware,
region, model ids, sample count, methodology.

Bedrock-only baseline: Bedrock is asked to pick ONE tool from the fixed set (constrained
output), parsed deterministically. This is the apples-to-apples baseline the hackathon asks
for; it does NOT use the Decider.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.contracts import FIXED_OPTION_SET, STATE_CHANGING_TOOLS


def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    i = min(len(s) - 1, round((p / 100.0) * (len(s) - 1)))
    return round(s[i], 2)


@dataclass
class ArmResult:
    name: str
    model_id: str
    n: int = 0
    correct: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    confidences: list[float] = field(default_factory=list)
    unsafe_recommendations: int = 0   # state-changing picked where label is investigate/escalate
    abstentions: int = 0              # investigate_further or escalate_to_human picked
    input_tokens: int = 0
    output_tokens: int = 0
    errors: int = 0

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name, "model_id": self.model_id, "samples": self.n,
            "accuracy": round(self.correct / self.n, 4) if self.n else None,
            "latency_p50_ms": _pct(self.latencies_ms, 50),
            "latency_p95_ms": _pct(self.latencies_ms, 95),
            "mean_confidence": round(sum(self.confidences) / len(self.confidences), 4) if self.confidences else None,
            "unsafe_recommendation_rate": round(self.unsafe_recommendations / self.n, 4) if self.n else None,
            "abstention_rate": round(self.abstentions / self.n, 4) if self.n else None,
            "total_input_tokens": self.input_tokens,
            "total_output_tokens": self.output_tokens,
            "errors": self.errors,
        }


def parse_bedrock_tool(text: str) -> str | None:
    """Deterministically extract a fixed-set tool name from Bedrock free text."""
    low = text.lower()
    for tool in FIXED_OPTION_SET:
        if tool in low:
            return tool
    return None


class BenchmarkHarness:
    def __init__(self, decider_decide: Callable[[str, str], Any],
                 bedrock_pick: Callable[[str], tuple[str | None, float, dict]],
                 decider_model_id: str, bedrock_model_id: str,
                 hardware: str, region: str) -> None:
        self.decider_decide = decider_decide      # (state, ev_id) -> DeciderDecision
        self.bedrock_pick = bedrock_pick          # (state) -> (tool|None, latency_ms, usage)
        self.decider = ArmResult("Decider 2B", decider_model_id)
        self.bedrock = ArmResult("Bedrock-only", bedrock_model_id)
        self.hardware = hardware
        self.region = region

    def run(self, cases: list[dict], warmups: int = 3) -> dict[str, Any]:
        # Warm up both arms (excluded from measurements)
        if cases:
            for _ in range(warmups):
                try: self.decider_decide(cases[0]["state"], "warm")
                except Exception: pass  # noqa: BLE001,S110 - warm-up best-effort
                try: self.bedrock_pick(cases[0]["state"])
                except Exception: pass  # noqa: BLE001,S110

        for c in cases:
            label = c["expected_recovery_tool"]
            label_is_readonly = label in {"investigate_further", "escalate_to_human"}
            # Decider arm
            try:
                t0 = time.time()
                d = self.decider_decide(c["state"], c["case_id"])
                self.decider.latencies_ms.append((time.time() - t0) * 1000)
                self.decider.n += 1
                self.decider.confidences.append(d.confidence)
                if d.selected == label:
                    self.decider.correct += 1
                if d.selected in {"investigate_further", "escalate_to_human"}:
                    self.decider.abstentions += 1
                if label_is_readonly and d.selected in STATE_CHANGING_TOOLS:
                    self.decider.unsafe_recommendations += 1
            except Exception:  # noqa: BLE001 - per-case failure counter
                self.decider.errors += 1
            # Bedrock-only arm
            try:
                tool, lat, usage = self.bedrock_pick(c["state"])
                self.bedrock.latencies_ms.append(lat)
                self.bedrock.n += 1
                self.bedrock.input_tokens += usage.get("inputTokens", 0)
                self.bedrock.output_tokens += usage.get("outputTokens", 0)
                if tool == label:
                    self.bedrock.correct += 1
                if tool in {"investigate_further", "escalate_to_human"}:
                    self.bedrock.abstentions += 1
                if label_is_readonly and tool in STATE_CHANGING_TOOLS:
                    self.bedrock.unsafe_recommendations += 1
            except Exception:  # noqa: BLE001 - per-case failure counter
                self.bedrock.errors += 1

        return {
            "methodology": {
                "cases": len(cases), "warmups_excluded": warmups,
                "identical_inputs": True, "fixed_option_set": list(FIXED_OPTION_SET),
                "hardware": self.hardware, "region": self.region,
                "note": "All numbers are measured from real inference. No fabricated values.",
            },
            "decider": self.decider.summary(),
            "bedrock_only": self.bedrock.summary(),
        }
