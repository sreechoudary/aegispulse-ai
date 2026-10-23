"""Benchmark harness logic tests (fakes, no real models)."""
from app.benchmark import BenchmarkHarness, parse_bedrock_tool


class FakeDecision:
    def __init__(self, selected, confidence): self.selected=selected; self.confidence=confidence


def test_parse_bedrock_tool_extracts_fixed_set():
    assert parse_bedrock_tool("I recommend rollback_deployment here") == "rollback_deployment"
    assert parse_bedrock_tool("nothing relevant") is None


def test_harness_computes_accuracy_and_rates():
    cases = [
        {"case_id":"c1","state":"s","expected_recovery_tool":"rollback_deployment"},
        {"case_id":"c2","state":"s","expected_recovery_tool":"investigate_further"},
    ]
    # Decider: correct on c1, picks state-changing on a read-only label for c2 (unsafe)
    dec_map = {"c1": FakeDecision("rollback_deployment",0.9), "c2": FakeDecision("scale_out_service",0.8),
               "warm": FakeDecision("rollback_deployment",0.9)}
    def dec(state, cid): return dec_map[cid]
    def bed(state): return ("investigate_further", 100.0, {"inputTokens":10,"outputTokens":5})
    h = BenchmarkHarness(dec, bed, "decider-x", "bedrock-y", "M4 Pro", "us-east-1")
    out = h.run(cases, warmups=1)
    assert out["decider"]["samples"] == 2
    assert out["decider"]["accuracy"] == 0.5            # c1 right, c2 wrong
    assert out["decider"]["unsafe_recommendation_rate"] == 0.5  # c2 unsafe
    assert out["bedrock_only"]["abstention_rate"] == 1.0        # always investigate
    assert out["methodology"]["note"].startswith("All numbers are measured")
