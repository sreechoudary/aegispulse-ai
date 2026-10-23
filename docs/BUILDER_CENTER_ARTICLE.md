# AegisPulse AI: Fast Decisions, Grounded Reasoning, Deterministic Safety

**Tags:** #strands-decider-2b #tool-selection
**Repository:** <REPO_URL_PLACEHOLDER>  ·  **Demo video:** <VIDEO_URL_PLACEHOLDER>

## The problem

When a production incident fires, the expensive minutes are the first ones: a human has to
read the telemetry, form a hypothesis, and choose a recovery action — roll back, scale out,
restart, keep investigating, or escalate. Large language models can reason about the evidence,
but they are slow for a decision you may need to make hundreds of times, they return free text
you then have to parse into an action, and they expose no calibrated confidence you can gate on.

AegisPulse AI is an autonomous incident commander that separates the *reasoning* from the
*decision* from the *authority to act* — and uses the right tool for each.

## Why Strands Decider 2B is central

Strands Decider 2B is a small, open decision model: it does not generate text, it reads a state
and a typed question and returns a choice with a calibrated confidence, in roughly a hundred
milliseconds on local hardware. That is exactly the shape of the recovery-tool decision. We hand
Decider 2B one typed `choice` question over a fixed set of five recovery tools and let it select,
fast, with a confidence number our policy layer can reason about. The decision pattern we
demonstrate is **#tool-selection**.

## The architecture: Decider selects, policy authorizes, Bedrock explains

The implemented call sequence for one incident is:

1. A deterministic simulator generates seeded incident telemetry.
2. The Strands agent gathers evidence (telemetry-reading tools) into an immutable snapshot.
3. **Amazon Bedrock** (`amazon.nova-lite-v1:0`) reads the evidence and writes a one-sentence
   root-cause assessment — the grounded reasoning.
4. **Strands Decider 2B** receives the state (telemetry summary + a contextual signal + the
   Bedrock assessment) and a typed `choice` question over the fixed tool set, and returns the
   selected tool with per-option probabilities and a calibrated confidence.
5. A **separate deterministic policy engine** authorizes or blocks that candidate — allowlist,
   evidence sufficiency, a configurable confidence threshold (default 0.90) applied only to
   automatic state-changing actions, and a blast-radius table.
6. High-blast-radius actions (rollback, scale-out) **always** require human approval, regardless
   of confidence. Approval is bound to the exact incident, action, parameters, and evidence
   snapshot, and expires.
7. The approved action executes against the **simulated** environment; the outcome and a full
   audit trail are persisted.

> The thesis, enforced in code: **the Decider SELECTS, the deterministic policy AUTHORIZES, and
> Bedrock EXPLAINS — nothing overrides the one before it.** The policy function never reads model
> text, so no amount of model output (or prompt injection) can reach a state-changing action
> without passing the deterministic gate and, where required, a human.

*(Architecture diagram: see `design.md` Mermaid diagrams; export `architecture.png` for the post.)*

## The typed tool-selection implementation

The request to the Decider serve endpoint (`POST /v1/systemone`) carries the state and one
`choice` question whose `criteria` describe *when each tool applies*:

```
questions = { "recovery_tool": { "type": "choice",
  "instructions": "Select the single best recovery tool for this incident.",
  "criteria": {
    "rollback_deployment": "Use ONLY when errors spiked right after a new deployment",
    "scale_out_service": "Use ONLY when CPU or request queue is saturated from high load",
    "restart_unhealthy_tasks": "Use ONLY when memory grows over time indicating a leak",
    "investigate_further": "Use when the cause is a resource limit where acting blindly is unsafe",
    "escalate_to_human": "Use when telemetry is contradictory or no single cause is clear" } } }
```

The response (`answers.recovery_tool.choice/.probabilities/.confidence`) is parsed into a typed,
validated decision. Out-of-set, malformed, or timed-out responses raise typed errors and the
policy fails closed.

## Human approval and fail-closed safety

Every high-blast-radius recommendation stops at a human. If the Decider is unavailable, returns a
tool outside the fixed set, or times out, the system fails closed: it blocks automatic
state-changing actions while still allowing read-only investigation and escalation. Idempotency
(at-most-once execution), a retry limit, and a hash-chained append-only audit log round out the
controls.

## Five incident scenarios + the Incident Time Machine

Bad Deployment, Capacity Saturation, Memory Leak, Database Connection Exhaustion, and an
Ambiguous Incident — each with deterministic, characteristic telemetry and an independently
labeled expected outcome. The **Incident Time Machine** replays a completed incident with modified
evidence through the *real* Decider and shows a field-level diff of tool, confidence, and policy
outcome. If the decision does not change, it says so — the comparison is the point, not a forced flip.

## Benchmark results and methodology (the honest version)

Our first benchmark showed Decider 2B at 40% tool-selection accuracy versus a Bedrock-only
baseline at 56%. We preserved that result and audited it rather than tuning it away. The gap was
ours: vague option descriptions and a stripped-down telemetry string, plus a Bedrock arm whose
abstentions happened to match some labels. After rewriting the typed question to describe *when*
each tool applies and grounding the state in the contextual facts a real incident carries —
developed on a held-out dev set, then measured **once** on the eval set — we ran a fair,
equal-context comparison (real inference, 50 cases, Apple M4 Pro / MPS, us-east-1):

**Evaluation A — equal-context tool selection:**
- Decider 2B: accuracy 1.00, p50 203 ms, p95 220 ms, 0% unsafe, Brier 0.118, ECE 0.276.
- Bedrock-only: accuracy 0.72, p50 535 ms, 48% abstention.

**Evaluation B — end-to-end agent under the same policy:**
- Hybrid (Bedrock → Decider → policy): selection accuracy 0.96, but slower end-to-end (p50 958 ms)
  because it pays for both calls.
- Bedrock-only agent: 0.72 accuracy, p50 496 ms. Both 0% unsafe — safety comes from the policy.

### Decider's measured advantage, and its limits

Decider 2B's durable, measured advantage here is **latency** (~2.5–3x faster than the Bedrock arm)
and **calibrated confidence**. Its accuracy is excellent *given well-engineered typed questions and
grounded evidence* — it is not an inherent property of the model; change the evidence
representation and the accuracy moves. We make no claim that Decider is categorically more accurate
than a frontier model.

### Limitations we are explicit about

- **50 evaluation cases is a small sample.** These are indicative engineering results, not
  statistical proof; treat few-point differences as noise.
- **Confidence calibration is imperfect** (ECE 0.276). The model was actually *under*-confident on
  our final eval (mean confidence 0.72 at 100% accuracy). Use confidence to route, not as truth.
- **The `context_signal` is simulator-provided.** In production that fact (e.g. "a deployment just
  completed") must come from real tooling such as a deployment tracker; our benchmark models that
  evidence, it does not prove the model infers it unaided.

## SDK integration lessons

Two things only surfaced against the real `strands-agents` 1.61.1 SDK, and both are now guarded by
regression tests:

- `strands.InterventionHandler` requires a `name` property — it is abstract; a handler that omits
  it cannot be instantiated.
- `before_tool_call(self, event, **kwargs)` receives a typed lifecycle *event* object (not loose
  arguments), and the action union includes a **`Transform`** action beyond Proceed / Deny /
  Confirm / Guide.

The HTTP serve contract was also worth pinning precisely: `questions` and `answers` are keyed
objects, and supplying `criteria` descriptions (available via the serve API, not the name-only CLI
form) materially improves selection quality.

## The reusable #tool-selection pattern

The decision lives in an independently importable package,
`patterns/confidence_aware_tool_router/`: the typed `ToolChoiceDecision`, the
`ConfidenceAwareToolRouter` that wraps the real `POST /v1/systemone` contract with validation and a
timeout, and `build_intervention_handler(router, policy)` that wires it into a Strands
`InterventionHandler`. Drop it into your own agent, hand it your option set and criteria, and gate
the result with your own policy. It depends on no AegisPulse application code.

## Setup (summary)

Authenticate AWS SSO, enable the Bedrock model, launch the Decider serve process locally
(Apple-silicon MPS or CPU/CUDA), start the FastAPI backend and the React frontend, and launch an
incident. Full steps are in the repository README.

---

*Decider predictions and confidence in AegisPulse AI are real model inference. Infrastructure
metrics and recovery outcomes are simulated. Strands Decider 2B is an experimental model; this is
an experimentation project, not a production incident-response system.*


## Prior art and differentiation

Autonomous-defense tooling is a crowded space, so it is worth being precise about what makes
AegisPulse AI distinct. Existing projects such as network intrusion-detection appliances (e.g.
packet-analysis systems that use classical ML to flag and auto-block malicious IPs) operate at the
network layer: their decision is an anomaly *classification* over packet features, and their
response is a direct, automatic block.

AegisPulse AI is a different thing in both the decision and the architecture:

- **Different decision.** AegisPulse hands a small, open *decision model* — Strands Decider 2B — a
  typed `choice` over a fixed set of operational recovery tools (rollback, scale-out, restart,
  investigate, escalate). It is tool selection for cloud incident response, not anomaly detection.
- **Reasoning is separate from the decision.** Amazon Bedrock produces the human-readable root-cause
  assessment; Decider 2B makes the calibrated, low-latency choice. Most autonomous-defense tools use
  a single classifier for both.
- **The model never authorizes action.** A separate deterministic policy engine decides what is safe
  to execute, and high-blast-radius actions always require explicit human approval regardless of
  model confidence. Auto-blocking appliances deliberately remove the human; AegisPulse deliberately
  keeps the human in the loop for high-impact actions.
- **Simulation-only and reproducible.** All remediation runs against a deterministic simulator;
  nothing mutates real infrastructure. The Incident Time Machine replays decisions counterfactually.

In short, where a network-defense appliance answers "is this traffic malicious, and should I block
it?", AegisPulse answers "given this incident, which recovery tool should a human approve?" — and it
is built specifically around the Strands Decider 2B #tool-selection pattern paired with Bedrock.
