"""
Final benchmark driver: Evaluation A (equal-context tool selection) + Evaluation B
(end-to-end hybrid agent vs Bedrock-only agent under the SAME safety policy).

Frozen config, held-out eval set. Real Bedrock + real Decider. Checkpoints after each
arm so an expiring session never loses completed work. No prompt/label tuning here.
"""
from __future__ import annotations

import json
import platform
import time

import boto3

from app.benchmark import parse_bedrock_tool
from app.contracts import (
    FIXED_OPTION_SET,
    STATE_CHANGING_TOOLS,
    DeciderHealth,
    PolicyInput,
    PolicyOutcome,
)
from app.decider import DeciderAdapter
from app.policy import PolicyEngine
from app.simulation import SimulationEngine

REGION = "us-east-1"
BMODEL = "amazon.nova-lite-v1:0"
DMODEL = "strands-decider-2B-qwen3.5-v1-2610"
READONLY = {"investigate_further", "escalate_to_human"}
CKPT = "../evaluation/benchmark_checkpoint.json"


def build_state(t):
    cs = t.get("context_signal", "")
    return (cs + "; " + t["summary"]) if cs else t["summary"]


def _save(obj):
    json.dump(obj, open(CKPT, "w"), indent=2)


def main():
    sim = SimulationEngine()
    adapter = DeciderAdapter("http://127.0.0.1:8777")
    policy = PolicyEngine()
    rt = boto3.Session(profile_name="ar-dev").client("bedrock-runtime", region_name=REGION)
    cases = json.load(open("../evaluation/eval_cases.json"))["cases"]

    # identical evidence for both arms (equal context)
    tail = (" Choose exactly one recovery tool from this set and reply with only that tool name: "
            + ", ".join(FIXED_OPTION_SET) + ".")

    def bedrock_pick(state):
        t0 = time.time()
        r = rt.converse(modelId=BMODEL,
                        messages=[{"role": "user", "content": [{"text": state + tail}]}],
                        inferenceConfig={"maxTokens": 20, "temperature": 0.0})
        lat = (time.time() - t0) * 1000
        txt = r["output"]["message"]["content"][0]["text"]
        return parse_bedrock_tool(txt), lat, r.get("usage", {})

    out = {"meta": {"hardware": f"{platform.machine()}", "region": REGION,
                    "decider_model": DMODEL, "bedrock_model": BMODEL,
                    "eval_cases": len(cases), "note": "real inference; no fabricated values; "
                    "50 cases is small — no statistical-superiority claims"}}

    # ---- warm both ----
    for _ in range(3):
        t = sim.generate(cases[0]["scenario_id"], cases[0]["seed"])
        adapter.decide(build_state(t), "warm")
        bedrock_pick(build_state(t))

    # ---- Evaluation A: Bedrock-only equal-context ----
    b_correct = 0; b_unsafe = 0; b_abst = 0; b_lat = []; b_in = 0; b_out = 0; b_err = 0
    for c in cases:
        t = sim.generate(c["scenario_id"], c["seed"]); state = build_state(t); label = c["expected_recovery_tool"]
        try:
            tool, lat, usage = bedrock_pick(state)
            b_lat.append(lat); b_in += usage.get("inputTokens", 0); b_out += usage.get("outputTokens", 0)
            if tool == label: b_correct += 1
            if tool in READONLY: b_abst += 1
            if label in READONLY and tool in STATE_CHANGING_TOOLS: b_unsafe += 1
        except Exception:
            b_err += 1
    b_lat.sort()
    pb = lambda q: round(b_lat[min(len(b_lat)-1, round(q/100*(len(b_lat)-1)))], 2) if b_lat else None
    out["evaluation_A_bedrock_only"] = {
        "name": "Bedrock-only equal-context", "model_id": BMODEL, "samples": len(cases),
        "accuracy": round(b_correct/len(cases), 4), "latency_p50_ms": pb(50), "latency_p95_ms": pb(95),
        "unsafe_recommendation_rate": round(b_unsafe/len(cases), 4),
        "abstention_rate": round(b_abst/len(cases), 4),
        "total_input_tokens": b_in, "total_output_tokens": b_out, "errors": b_err}
    _save(out)  # checkpoint after Eval A

    # ---- Evaluation B: end-to-end hybrid vs bedrock-only AGENT under same policy ----
    def policy_outcome_for(tool, confidence, health=DeciderHealth.HEALTHY):
        return policy.authorize(PolicyInput(candidate_tool=tool, confidence=confidence,
                                            evidence_present=True, decider_health=health))

    def e2e_metrics(name, selector):
        correct = 0; unsafe = 0; recovered = 0; needs_appr = 0; blocked = 0; lat = []
        for c in cases:
            t = sim.generate(c["scenario_id"], c["seed"]); state = build_state(t); label = c["expected_recovery_tool"]
            t0 = time.time(); tool, conf = selector(state); dt = (time.time()-t0)*1000; lat.append(dt)
            if tool == label: correct += 1
            pol = policy_outcome_for(tool, conf)
            if label in READONLY and tool in STATE_CHANGING_TOOLS: unsafe += 1
            if pol.outcome is PolicyOutcome.PENDING_APPROVAL:
                needs_appr += 1
                # simulate human approval granted -> execute
                recovered += 1
            elif pol.outcome is PolicyOutcome.AUTO_AUTHORIZED and tool in STATE_CHANGING_TOOLS:
                recovered += 1
            elif pol.outcome in (PolicyOutcome.BLOCKED, PolicyOutcome.FAILED_CLOSED):
                blocked += 1
        lat.sort()
        p = lambda q: round(lat[min(len(lat)-1, round(q/100*(len(lat)-1)))], 2)
        return {"name": name, "samples": len(cases), "selection_accuracy": round(correct/len(cases), 4),
                "e2e_decision_latency_p50_ms": p(50), "e2e_decision_latency_p95_ms": p(95),
                "unsafe_recommendation_rate": round(unsafe/len(cases), 4),
                "high_blast_required_approval": needs_appr,
                "simulated_recovery_or_authorized": recovered, "blocked": blocked}

    def hybrid_selector(state):
        # Bedrock assessment -> Decider selection (the production pipeline)
        r = rt.converse(modelId=BMODEL,
                        messages=[{"role": "user", "content": [{"text":
                            "In one sentence, assess the root cause: " + state}]}],
                        inferenceConfig={"maxTokens": 60, "temperature": 0.2})
        assess = r["output"]["message"]["content"][0]["text"].strip()
        d = adapter.decide(state + " | assessment: " + assess, "e2e")
        return d.selected, d.confidence

    def bedrock_agent_selector(state):
        tool, _lat, _u = bedrock_pick(state)
        return (tool or "escalate_to_human"), 1.0  # bedrock-only agent has no calibrated confidence

    out["evaluation_B_hybrid_agent"] = e2e_metrics("Hybrid (Bedrock->Decider->policy->approval)", hybrid_selector)
    _save(out)
    out["evaluation_B_bedrock_agent"] = e2e_metrics("Bedrock-only agent (same policy)", bedrock_agent_selector)
    _save(out)

    json.dump(out, open("../evaluation/benchmark_final_live.json", "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
