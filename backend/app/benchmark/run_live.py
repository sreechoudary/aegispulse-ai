"""
Live benchmark driver (Phase 5). Real Decider 2B vs Bedrock-only on the 50 labeled cases.
Builds each case's `state` deterministically from the simulation telemetry summary, so both
arms see identical inputs. Writes evaluation/benchmark_report.json. No fabricated numbers.
"""
from __future__ import annotations

import json
import platform
import time

import boto3

from app.benchmark import BenchmarkHarness, parse_bedrock_tool
from app.contracts import FIXED_OPTION_SET
from app.decider import DeciderAdapter
from app.simulation import SimulationEngine

REGION = "us-east-1"
BEDROCK_MODEL = "amazon.nova-lite-v1:0"
DECIDER_MODEL = "strands-decider-2B-qwen3.5-v1-2610"
DECIDER_ENDPOINT = "http://127.0.0.1:8777"


def build_states():
    sim = SimulationEngine()
    cases = json.load(open("../evaluation/eval_cases.json"))["cases"]
    for c in cases:
        t = sim.generate(c["scenario_id"], c["seed"])
        c["state"] = t["summary"]
    return cases


def main():
    cases = build_states()
    adapter = DeciderAdapter(DECIDER_ENDPOINT)
    rt = boto3.Session(profile_name="ar-dev").client("bedrock-runtime", region_name=REGION)

    def decider_decide(state, cid):
        return adapter.decide(state, cid)

    prompt_tail = (" Choose exactly one recovery tool from this set and reply with only that "
                   "tool name: " + ", ".join(FIXED_OPTION_SET) + ".")
    def bedrock_pick(state):
        t0 = time.time()
        r = rt.converse(modelId=BEDROCK_MODEL,
                        messages=[{"role": "user", "content": [{"text": state + prompt_tail}]}],
                        inferenceConfig={"maxTokens": 20, "temperature": 0.0})
        lat = (time.time() - t0) * 1000
        txt = r["output"]["message"]["content"][0]["text"]
        return parse_bedrock_tool(txt), lat, r.get("usage", {})

    hw = f"{platform.machine()} {platform.processor() or platform.system()}"
    h = BenchmarkHarness(decider_decide, bedrock_pick, DECIDER_MODEL, BEDROCK_MODEL, hw, REGION)
    report = h.run(cases, warmups=3)
    open("../evaluation/benchmark_report.json", "w").write(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
