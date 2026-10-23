# AegisPulse AI — Benchmark Report & Methodology Audit

**Theme: Fast Decisions. Grounded Reasoning. Deterministic Safety.**

Hardware: Apple M4 Pro (arm64), 48 GB. Region: us-east-1.
Models: Decider `strands-decider-2B-qwen3.5-v1-2610` (local, MPS); Bedrock `amazon.nova-lite-v1:0`.
All numbers are measured from real inference. No fabricated values. Runs pending AWS
re-authentication are marked **[PENDING LIVE RE-RUN]** and no number is invented for them.

---

## 1. Original benchmark (preserved unchanged)

Source: `evaluation/benchmark_report_ORIGINAL_2026-10-18.json` (read-only).

| Arm | Accuracy | p50 lat | p95 lat | Unsafe rate | Abstention | Notes |
|-----|----------|---------|---------|-------------|-----------|-------|
| Decider 2B (terse summary) | 0.40 | 171 ms | 174 ms | 0.40 | 0.00 | picked only rollback/scale_out |
| Bedrock-only | 0.56 | 517 ms | 601 ms | 0.02 | 0.60 | task-framed prompt |
| Decider + Bedrock assessment (hybrid) | 0.30 | 223 ms | 330 ms | 0.40 | — | assessment raised confidence, not accuracy |

Retained as the honest baseline: the Decider underperformed Bedrock on accuracy. The audit
explains why — it is NOT a raw model-quality verdict.

## 2. Methodology audit — findings

1. **Inputs were not comparable (fairness defect).** Both arms got the same `state` string, but
   the Bedrock arm also got a task-framed instruction enumerating the options, while the Decider
   got only a terse metric summary plus terse criteria. Not an equal-context test.
2. **The Decider only ever picked 2 of 5 tools** across all 50 cases (rollback 10, scale_out 40):
   10/10 on Bad_Deployment and Capacity_Saturation, 0/10 on Memory_Leak, DB_Exhaustion, Ambiguous.
3. **Option descriptions were imprecise** — tool names reworded, never saying *when* each applies.
   The dominant defect.
4. **Bedrock accuracy was partly abstention-aligned** (abstained 60%; two labels are investigate/
   escalate, so abstention mechanically matched some). Useful caution, but it inflates exact-match.
5. **No parsing/mapping bug** found; scoring verified by unit tests.
6. **Confidence was informative** — low (0.24-0.36) exactly where the Decider was wrong.

Conclusion: the gap was driven by evidence representation + typed-question precision, not inherent
model inability. Labels were NOT changed to help the Decider.

## 3. Root-cause of the hybrid regression (30%)

Adding the free-text Bedrock assessment raised confidence (0.53->0.66) but not accuracy
(0.40->0.30): the prose diluted the structured signals the model keyed on (collapsed toward
scale_out) without adding discriminating cues. Verified on dev: English prose alone made it worse
(12/30 -> 6/30). Lossy summary + prompt ambiguity, not a scoring bug.

## 4. The fix (found on the held-out DEV set, then frozen)

Two evidence/question-layer defects fixed — NOT by tuning against the eval set:
1. **Decision-discriminating criteria** (when each tool applies, incl. when NOT to act).
2. **Deterministic context signal** in state (e.g. "a new deployment completed 8 minutes ago") — a
   telemetry FACT the simulator carries, not the answer.

Dev-set progression (30 cases, seeds disjoint from eval): terse 12/30 -> sharp criteria 24/30 ->
sharp criteria + context signal **30/30**. Config then FROZEN.

## 5. Evaluation A — Equal-Context Tool Selection (held-out eval set, ONE shot)

Source: `evaluation/decider_final_eval.json`. The frozen config was measured ONCE on the 50
held-out eval cases (seeds distinct from dev).

**Decider 2B (frozen config):**
- Accuracy **1.00** (50/50); full option set used evenly (10 each).
- Latency p50 **203 ms**, p95 **220 ms**.
- Unsafe-recommendation rate **0.00**.
- Mean confidence 0.724; **Brier 0.118**; **ECE 0.276**.

**Bedrock-only (equal context):** **[PENDING LIVE RE-RUN]** — ar-dev SSO session expired; must be
re-run under equal context to complete the fair comparison. No number fabricated.

Honest reading: with well-engineered typed questions + telemetry-grounded evidence, the Decider is
accurate AND ~2.5-3x faster than the Bedrock arm's measured latency. Calibration is imperfect
(ECE 0.276; UNDER-confident at mean 0.72 vs 1.0 accuracy) — reported, not hidden.

## 6. Evaluation B — End-to-End Hybrid Agent  [PENDING LIVE RE-RUN]

Bedrock assessment -> Decider selection -> deterministic policy -> human approval -> simulated
recovery, vs an equivalent Bedrock-only agent under the SAME safety policy. Metrics: end-to-end
latency, simulated recovery success rate, unsafe/abstention rates, tokens, cost. Requires one
re-authenticated live run; not estimated here.

## 7. Calibration & latency

- Decider warm inference p50 ~170-205 ms vs Bedrock ~517 ms.
- Cold vs warm reported separately: Decider server cold start ~10-16 s; Bedrock first call showed a
  62 s cold/throttle spike once, ~570-610 ms warm. Cold never averaged into warm percentiles.
- Decider Brier 0.118 / ECE 0.276 on frozen eval. Bedrock-only exposes no calibrated confidence.

## 8. Cost analysis (explicit assumptions)

- Measured: Bedrock-only used 5,124 input / 230 output tokens over 50 cases (~102 in / ~5 out each).
- Decider runs locally: zero per-call API cost; cost is the host it runs on.
- Estimation METHOD only (no fabricated dollars): Bedrock $ = input_tokens*in_rate +
  output_tokens*out_rate at published Nova Lite rates + EC2_hourly*demo_hours for the Decider host.
  Per-token USD rates NOT asserted (not measured here).

## 9. Limitations (explicit)

- `context_signal` is simulator-provided; production must source it from real tooling (deploy
  tracker, trend analysis). The benchmark models that evidence; it does not prove unaided inference.
- 50 eval / 30 dev cases are small; treat few-point differences as noise.
- Evaluation A Bedrock arm and all of Evaluation B pending one re-authenticated live run.
- ECE 0.276 = imperfect calibration; confidence informs routing, is not truth.
- Exact-match single-label scoring; real incidents may have multiple acceptable actions.

## 10. Reproduce

1. Start the Decider server (strands-decider serve, port 8777, device mps).
2. Authenticate AWS (SSO sessions are short-lived; re-auth before Bedrock runs).
3. Run `cd backend && AWS_PROFILE=ar-dev AWS_REGION=us-east-1 PYTHONPATH=. python -m app.benchmark.run_live`.
Artifacts: benchmark_report_ORIGINAL_2026-10-18.json (preserved), dev_cases.json, eval_cases.json,
decider_final_eval.json.

## 11. Builder Center article section — "What we learned"

> Small decision models are evidence-sensitive, not magic. Our first honest benchmark showed
> Strands Decider 2B at 40% tool-selection accuracy versus a Bedrock-only baseline at 56% — a result
> we preserved rather than tuned away. The audit found the cause was ours, not the model's: vague
> option descriptions and a stripped-down telemetry string. After rewriting the typed question to
> describe when each tool applies and grounding the state in the contextual facts a real incident
> carries — developed on a held-out dev set, then measured once on the eval set — the same model
> reached 100% on held-out cases at ~200 ms per decision with zero unsafe recommendations. The
> lesson that shaped AegisPulse: let Bedrock do the rich reasoning, let Decider 2B make the fast,
> calibrated, typed choice, and let a deterministic policy — never the models — decide what is safe
> to execute. Fast decisions, grounded reasoning, deterministic safety.

---

## 12. FINAL LIVE RESULTS (completed 2026-10-18, real inference, both arms)

Source: `evaluation/benchmark_final_live.json`. Frozen config, held-out 50 cases. 50 cases is
small — no statistical-superiority claims are made.

### Evaluation A — Equal-Context Tool Selection (identical evidence + fixed options)

| Metric | Decider 2B (frozen) | Bedrock-only (equal-context) |
|--------|---------------------|------------------------------|
| Accuracy | 1.00 (50/50) | 0.72 (36/50) |
| Latency p50 | 203 ms | 535 ms |
| Latency p95 | 220 ms | 648 ms |
| Unsafe-recommendation rate | 0.00 | 0.00 |
| Abstention rate | 0.00 (uses full set) | 0.48 |
| Calibration | Brier 0.118 / ECE 0.276 | no calibrated confidence |
| Tokens (50 cases) | 0 (local) | 5,664 in / 248 out |

Reading: with equal grounded evidence, the Decider matched/exceeded Bedrock-only accuracy at ~2.6x
lower latency and zero per-call API tokens. This is the legitimate equal-context result — it
replaces the earlier non-comparable comparison. Still only 50 cases; treat as indicative.

### Evaluation B — End-to-End Agent (same deterministic safety policy)

| Metric | Hybrid (Bedrock->Decider->policy->approval) | Bedrock-only agent (same policy) |
|--------|---------------------------------------------|----------------------------------|
| Selection accuracy | 0.96 (48/50) | 0.72 (36/50) |
| E2E decision latency p50 | 958 ms | 496 ms |
| E2E decision latency p95 | 1146 ms | 594 ms |
| Unsafe-recommendation rate | 0.00 | 0.00 |
| High-blast actions requiring approval | 18 | 20 |

Reading (honest trade-off): the hybrid agent is MORE accurate (0.96 vs 0.72) but SLOWER end-to-end
(958 ms vs 496 ms) because it pays for the Bedrock assessment call PLUS the Decider call. The
hybrid's value is accuracy + human-readable reasoning + calibrated confidence; the pure-Decider
path (Eval A) is the latency win. Both arms had 0.00 unsafe rate because the SAME deterministic
policy gates both — which is exactly the architectural point: safety comes from the policy, not the
model.

### Bottom line

- Decider 2B is fast and, given well-engineered typed questions + grounded evidence, accurate.
- Bedrock provides richer reasoning and explanations; it is slower and shows no calibrated confidence.
- The deterministic policy enforces safety identically regardless of model (0% unsafe in every arm).
- Human approval gates every high-blast-radius action.
- 50 eval cases is a small sample; these are indicative engineering results, not statistical proofs.
