# AegisPulse AI — Video Storyboard (max 3:00)

**Title card:** AegisPulse AI — Fast Decisions. Grounded Reasoning. Deterministic Safety.
**Tags shown:** #strands-decider-2b #tool-selection

## Pre-record readiness (do all before hitting record)
- Decider serve process up and READY (warm). Fire one throwaway incident to warm it.
- AWS SSO authenticated (session is short-lived — authenticate immediately before recording).
- Backend + frontend running; backend "● online" badge green in the header.
- Do a full dry run once so the on-camera Bedrock + Decider calls are warm (~200ms Decider, ~570ms Bedrock), not the ~62s cold spike.

## Storyboard

| # | Time | Screen action | Narration (verbatim) |
|---|------|---------------|----------------------|
| 1 | 0:00–0:15 | Title card -> dashboard header | "This is AegisPulse AI, an autonomous incident commander. It pairs the real Strands Decider 2B model with Amazon Bedrock, behind a deterministic safety policy." |
| 2 | 0:15–0:30 | Incident Arena, hover the 5 cards; click **Bad Deployment** | "Five realistic incident scenarios. I'll launch a bad deployment — error rates just spiked after a release." |
| 3 | 0:30–0:50 | Agent timeline fills; Bedrock Assessment panel renders | "The agent gathers telemetry, and Amazon Bedrock reasons about the root cause. This is live inference — labeled REAL." |
| 4 | 0:50–1:15 | Decision Observatory: confidence bars, latency, model id | "Now Strands Decider 2B makes the call. It's a decision model — no text generation — it returns a typed choice with calibrated confidence in about two hundred milliseconds. It picked rollback." |
| 5 | 1:15–1:35 | Point to policy gate = PendingApproval | "Here's the key design point: the Decider recommends, it does not authorize. A separate deterministic policy requires human approval for high-blast-radius actions like rollback — no matter how confident the model is." |
| 6 | 1:35–1:50 | Click **Approve**; recovery card turns green | "A human approves. The simulated rollback runs, MTTR is measured, and the full decision is persisted to an audit trail. Nothing touches real infrastructure." |
| 7 | 1:50–2:15 | Incident Time Machine: click Replay; diff table | "The Incident Time Machine replays the same incident with changed evidence — through the real model — and shows what changed. If the decision holds, we show that honestly." |
| 8 | 2:15–2:40 | Cut to benchmark chart / report | "On an equal-context benchmark of fifty cases, Decider 2B matched accuracy at roughly three times lower latency than the Bedrock-only baseline. It's a small sample, and calibration isn't perfect — we document both." |
| 9 | 2:40–2:55 | Show the reusable package README | "The decision lives in a reusable tool-selection pattern any builder can drop into their own Strands agent." |
| 10 | 2:55–3:00 | Title card | "Fast decisions, grounded reasoning, deterministic safety. AegisPulse AI." |

## Fallback guidance (if Bedrock is slow or throttles on camera)
- If the Bedrock assessment hangs beyond ~3s, say: "Bedrock is doing its reasoning pass" and let it
  land — do NOT cut to a fake result. The retry/backoff handles transient throttling automatically.
- If Bedrock errors on camera, the UI shows an error state; narrate: "Bedrock is unavailable, so the
  policy fails closed — the agent falls back to investigate/escalate, never an unsafe action." Then
  re-shoot after re-authenticating. This is a legitimate safety demonstration, not a failure.
- If the Decider server dropped, the decide call shows a fail-closed state; restart the serve process
  (readiness check) and re-shoot the decision beat.
- Keep a pre-warmed second incident ready so you can re-shoot a beat without a cold start.
- NEVER substitute prerecorded or fabricated model output. Live inference must be genuine.

## Capture checklist
- [ ] 1080p+, dark theme, legible font scaling.
- [ ] Footer visible at least once (REAL vs SIMULATED disclaimer).
- [ ] Both hashtags visible on screen.
- [ ] Total runtime < 3:00.
- [ ] Captions/transcript for accessibility.
