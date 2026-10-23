# AegisPulse AI — 3-Minute Demo Script

**Tagline:** Fast Decisions. Grounded Reasoning. Deterministic Safety.
**Hashtags:** #strands-decider-2b #tool-selection

## Pre-flight (keep models warm BEFORE recording)
1. Start the Decider server and wait for readiness (~10-16s cold): `strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --device mps --port 8777`
2. Authenticate AWS: `aws sso login --profile ar-dev` (SSO sessions are short-lived; do this right before).
3. Start the backend (uvicorn) and the frontend (`npm run dev`).
4. Fire ONE warm-up incident so the first on-camera Bedrock + Decider calls are warm (avoid the ~62s cold spike).
5. Keep live inference visible. Do NOT use prerecorded or fabricated results.

## Script (target ~2:45)
| Time | Action | Narration |
|------|--------|-----------|
| 0:00 | Open dashboard | "AegisPulse AI - an autonomous incident commander. Real Strands Decider 2B, real Bedrock, deterministic safety." |
| 0:15 | Click Bad Deployment | "A release just spiked 5xx errors. The agent investigates real telemetry." |
| 0:30 | Bedrock Assessment panel | "Amazon Bedrock reasons about root cause - live inference, labeled REAL." |
| 0:50 | Decision Observatory | "Strands Decider 2B picks the recovery tool - rollback - with calibrated confidence, in ~200ms." |
| 1:10 | Policy gate = PendingApproval | "Decider recommends; it does NOT authorize. A separate deterministic policy requires human approval for high-blast-radius actions, regardless of confidence." |
| 1:25 | Click Approve | "A human approves the simulated rollback." |
| 1:35 | Recovered | "Simulated recovery succeeds - MTTR measured, full audit trail persisted. Nothing touches real infrastructure." |
| 1:55 | Incident Time Machine replay | "Counterfactual replay through the real model - change the evidence, see if the decision changes. If it does not, we show that honestly." |
| 2:20 | Reusable pattern README | "The decision pattern - Confidence-Aware Recovery Tool Router - is an independently reusable #tool-selection package." |
| 2:35 | Close | "Fast decisions from Decider 2B, grounded reasoning from Bedrock, safety from a deterministic policy. That's AegisPulse AI." |

## Honesty guardrails (on screen)
- Footer always reads: "Decider predictions & confidence are REAL model inference. Infrastructure metrics & recovery outcomes are SIMULATED."
- Do not claim Decider beats Bedrock on accuracy without the equal-context benchmark on screen.
- If replay does not flip the tool, say so - the comparison mechanism is the point, not a forced flip.
