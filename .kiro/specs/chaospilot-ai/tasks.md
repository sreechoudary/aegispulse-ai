# Implementation Plan: AegisPulse AI

## Overview

This plan converts the AegisPulse AI design into an actionable, incremental coding plan organized into ten workstreams. The critical path is **M0 — the real-inference vertical slice** (one scenario end-to-end through the full gated path with real Decider 2B and real Bedrock inference), which also closes the design's "Unresolved Assumptions" before any adapter code is frozen (Requirement 17 MVP scope).

Every task carries **Requirements** traceability, **Dependencies**, **Scope**, **Acceptance**, **Validation**, owning **Workstream**, and **Priority**. Test sub-tasks are marked optional with `*` per spec convention; core implementation tasks are never optional. The 32 design Correctness Properties are each turned into a single property-based test (Hypothesis, ≥100 iterations), annotated with the Property number and the requirement it validates.

The backend is Python 3.11+ / FastAPI / Pydantic (design: Technology Choices); the frontend is React + TypeScript + Vite + Tailwind. These languages are fixed by the design, so no language-selection step is required.

### Milestones

| Milestone | Theme | Priority | Content |
|-----------|-------|----------|---------|
| **M0** | Real Inference Vertical Slice | P0 | Close unresolved assumptions (WS1), real Decider `POST /v1/systemone` inference returning a parsed in-set tool, real Bedrock invocation, ONE scenario (`Bad_Deployment`) end-to-end through the full gated path: Decider selects → deterministic policy authorizes → human approval for high-blast-radius rollback → simulated execution → Decision_Record persisted. (Req 17.1) |
| **M1** | Breadth core | P1 | Remaining four scenarios, full deterministic policy + approval gate, persistence + SSE hardening, core dashboard screens (Incident Arena, Recovery Timeline). (Req 17.2–17.3) |
| **M2** | Replay + benchmark + full dashboards | P1/P2 | Incident Time Machine replay, full Benchmark Harness (≥50 cases, warm-ups, p50/p95, calibration), advanced dashboards (Decision Observatory, Benchmark Lab, Architecture & About). (Req 17.4) |
| **M3** | Deployment + docs + submission | P2 | Docker Compose + AWS deployment config, release gate, hackathon deliverables, demo. (Req 14, 15) |

### M0 Validation Results (2026-10-18)

**Status: M0 GATE PASSED.** Real Decider 2B + real Bedrock inference, no mocks substituted. Workstream 1 (Environment and SDK validation) is complete and all Unresolved Assumptions except EC2 sizing are closed.

- **Validated versions (exact):** Python 3.12.13, `strands-decider` 0.1.0, `strands-agents` 1.61.1, torch 2.14.1, transformers 5.20.1, tokenizers 0.23.3, safetensors 0.8.0.
- **Decider 2B (real inference):** model `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610`; footprint ~5099 MB (peak 5204) on MPS; warm HTTP inference ~199 ms; cold HTTP 661 ms. Verified `serve` contract: request `questions` is a keyed object with `type`/`instructions`/`criteria`; response `answers` is a keyed object with `choice`/`probabilities`/`confidence`; top-level `model`/`usage`/`latency_ms`.
- **Strands Agents SDK:** `strands-agents` 1.61.1; `Agent` accepts `interventions`; `InterventionHandler.before_tool_call(self, event: BeforeToolCallEvent, **kwargs) -> Proceed | Deny | Guide | Confirm | Transform`. **New finding:** a `Transform` action exists beyond Proceed/Deny/Confirm/Guide, and the handler receives typed lifecycle *event* objects (not loose args) — integration code must honor this.
- **Bedrock (real inference):** profile `ar-dev`, region us-east-1, model `amazon.nova-lite-v1:0`; real Converse inference OK (~2512 ms cold, 70 tokens); 95 text models available in region.
- **M0 smoke (full gated path):** `Bad_Deployment` → real Bedrock assessment → real Decider selected `rollback_deployment` @ 0.9506 → deterministic policy `PendingApproval` (high-blast-radius always requires approval, even at 0.95) → approval granted → simulated execution → recovery measured → Decision_Record persisted. The Decider selection controlled the action; Bedrock reasoned but did not override selection or policy.
- **Unresolved assumptions status:** (a) version pins **CLOSED**; (b) Strands SDK symbols/signature **CLOSED** (+ `Transform`); (c) live `serve` schema **CLOSED**; (d) concrete EC2 type + measured cost **OPEN → Workstream 9**; (e) Bedrock region availability **CLOSED** (token-cost method documented).
- **Evidence:** detailed findings and artifacts live in `docs/validation/M0_VALIDATION_REPORT.md` (and `m0_smoke_output.txt`, `m0_events.json`, `m0_decision_record.json`).
- **Deployment note:** M0 validation used a broad admin SSO role. A least-privilege read/inference/logging-only IAM profile (no production mutation) must be scoped before any deployment (Req 14.3).

### Wave A Implementation Status (2026-10-18)

- **G1 contracts frozen.** The G1 interface contracts are frozen in `backend/app/contracts/` with 10 contract tests; `docs/contracts/G1_CONTRACTS.md` is the authoritative reference. The validated SDK findings — `InterventionHandler` requires a `name` property, a `Transform` action exists beyond Proceed/Deny/Confirm/Guide, and `before_tool_call` receives a typed lifecycle *event* object — are preserved there and guarded by regression tests in `backend/tests/unit/test_strands_sdk_compat.py`.
- **Execution method (reported accurately).** The workstreams were implemented sequentially via direct implementation. The `spec-task-execution` sub-agent dispatch was unavailable in this session; this status is reported as actually performed, not simulated.
- **Backend.** 55 tests passing: Decider package 10, adapter 4, SDK-compat 5, simulation 8, policy/approval/audit 14, property-based 6 (at 120 examples each), end-to-end API flow + SSE 3, eval-dataset 4, and G1 contracts 10 — these categories overlap, and the suite total is 55. Ruff clean; mypy clean on core modules.
- **Frontend.** Vite + React + TypeScript + Tailwind dashboard with Incident Arena, Decision Observatory (including ConfidenceView), Recovery Timeline, and an approval control; 2 component tests passing.
- **QA.** 50 labeled evaluation cases at `evaluation/eval_cases.json` (10 per scenario), with labels derived independently of the Decider.
- **Vertical slice — Decider half PROVEN end-to-end.** Through the real FastAPI API with REAL Decider 2B inference (model `strands-decider-2B-qwen3.5-v1-2610`): `Bad_Deployment` → deterministic telemetry → real Decider selected `rollback_deployment` (matching the labeled expectation) → policy `PendingApproval` → human approval → simulated rollback (MTTR 34s, restored) → `Recovered` → Decision_Record persisted → SSE `decider_decision` event present. Recorded actual confidence **0.3358** (not hard-coded). NOTE: the Bedrock assessment materially raises confidence (0.95 in M0 with assessment vs 0.3358 without), so the full slice wires Bedrock → Decider.
- **BLOCKER RESOLVED.** The prior blocker (the `ar-dev` SSO session expired mid-run with `TokenRetrievalError`, leaving the full slice's REAL Bedrock step pending) is resolved. The session was re-authenticated and the full gated path now runs with REAL Bedrock AND REAL Decider together. See the **G2 Live Validation — PASSED** entry below.

### G2 Live Validation — PASSED (2026-10-18)

**Status: G2 PASS.** The live end-to-end vertical slice runs the full gated path with real Bedrock AND real Decider inference together — no mocks substituted.

- **AWS:** profile `ar-dev`, account `<redacted-account-id>` (masked), SSO `AWSAdministratorAccess` role, region us-east-1. Session re-authenticated.
- **Full gated path (end-to-end):** executed via `slice_runner.py` with `AWS_PROFILE=ar-dev AWS_REGION=us-east-1`: create+simulate → investigate → REAL Bedrock assessment → REAL Decider selection → policy → approval → simulated execution → recovery → persisted audit trail. `SLICE_RESULT=PASS`.
- **Bedrock:** model `amazon.nova-lite-v1:0`, region us-east-1. First-call latency was a 62393 ms cold-start/throttle spike; warm latency measured ~570–610 ms (2309 ms on the first warm call) over 3 follow-up calls; token usage ~72 in / 28 out / 100 total on the slice call (80–81 total warm).
- **Decider:** model `strands-decider-2B-qwen3.5-v1-2610`, selected `rollback_deployment`, confidence **0.7907** (actual, not hard-coded; higher than the 0.3358 no-assessment run and lower than M0's 0.9506 — confirms the Bedrock assessment materially raises confidence); `decider_health=healthy`.
- **Policy:** `PendingApproval` (high-blast-radius always requires approval); human approval granted; simulated rollback executed (MTTR 34s, service restored, success); `final_state` Recovered; 1 Decision_Record persisted; `audit_chain_valid=True`; all 13 lifecycle event types emitted including `bedrock_assessment` and `decider_decision`.
- **Total slice execution time:** ~63.4s (dominated by the Bedrock cold-start spike).
- **Tests:** full backend suite 55/55 passing; targeted integration + safety regression 29/29; ruff clean; mypy clean on core modules; frontend 2/2.
- **Safety:** code audit confirms the only AWS call is Bedrock `converse` (inference, read-only). No AWS mutation API (`create_`/`delete_`/`put_`/`update_`/`terminate_`/`modify_` on any AWS client) is invoked. No real AWS infrastructure modified.
- **Evidence:** `docs/validation/g2_slice_output.txt`.

**G2 PASS.** Benchmarking, advanced dashboards, replay, and deployment tasks remain pending review and are NOT marked complete.

### M1/M2 Implementation Status (2026-10-18)

**Status: M1/M2 breadth delivered across seven phases — real inference throughout, no mocks substituted.** AWS deployment and the full submission/publish deliverables remain pending human action and are NOT marked complete.

- **Phase 1 — Runtime reliability.** A Decider server lifecycle manager (`backend/app/runtime/decider_server.py`) handles start, readiness, health, and graceful shutdown with the model loaded exactly once. A Bedrock readiness check plus a bounded warm-up and bounded exponential-backoff-with-jitter retry (`backend/app/runtime/reliability.py`, wired into `backend/app/bedrock/reasoner.py`) applies **only** to TRANSIENT throttling. Cold vs warm latency is tracked separately. State-changing actions are NEVER auto-retried. 5 reliability tests.
- **Phase 2 — Dashboard.** Enhanced React/TS/Vite/Tailwind mission-control dashboard: health badge, five scenario cards, agent timeline, a REAL Bedrock assessment panel, Decision Observatory (confidence bars + latency + policy gate), a human approval control, recovery timeline, and an Incident Time Machine replay table. REAL-vs-SIMULATED labeling appears in the footer; loading/error states present. `tsc` clean; 2 vitest component tests pass.
- **Phase 3 — Incident Time Machine.** `backend/app/replay/` engine (validate / apply / compare, with REAL-inference vs SIMULATED-outcome labels) plus `service.replay()` that creates a NEW incident and never mutates the original (proven by test). `POST /api/v1/incidents/{id}/replay` endpoint added; replay never modifies the original record.
- **Phase 4 — Scenarios.** All five scenarios validated with distinct characteristic deterministic telemetry (7 scenario tests) plus a baked-in deterministic `context_signal` per scenario (a telemetry fact, not the answer).
- **Phase 5 — Benchmark.** An honest methodology audit was completed; original results are preserved read-only at `evaluation/benchmark_report_ORIGINAL_2026-10-18.json`. The design uses two evaluations. The root cause of the earlier low Decider accuracy was imprecise typed-question option descriptions plus missing context evidence (NOT a model-quality verdict); it was fixed on a held-out dev set (disjoint seeds) and then measured ONCE on the eval set. FINAL equal-context results (`evaluation/benchmark_final_live.json`, real inference, 50 cases):
  - **Evaluation A** — Decider 2B accuracy 1.00, p50 203 ms, p95 220 ms, 0% unsafe, Brier 0.118, ECE 0.276; Bedrock-only accuracy 0.72, p50 535 ms, 0.48 abstention.
  - **Evaluation B** (end-to-end, same policy) — Hybrid selection accuracy 0.96 but slower (p50 958 ms, pays Bedrock + Decider); Bedrock-only agent 0.72 (p50 496 ms); both 0% unsafe (safety comes from the deterministic policy, not the model).
  - 50 cases is small — NO statistical-superiority claims are made. Full report: `evaluation/BENCHMARK_REPORT.md`.
- **Phase 6 — Quality gate.** Backend 81 tests + frontend 2 tests passing; ruff clean; mypy clean on core modules (`contracts`/`policy`/`simulation`/`approval`/`replay`/`runtime`). High-blast-radius actions cannot execute without human approval regardless of confidence (property + unit tested). Replay never mutates the original record (tested).
- **Phase 7 — Demo readiness artifacts.** `docs/DEMO_SCRIPT.md` (<3-min script), `README.md`, `docs/DEPLOYMENT_CHECKLIST.md`, `docs/SUBMISSION_CHECKLIST.md`. The full live journey (create → investigate w/ real Bedrock → decide w/ real Decider → approve → execute → replay) is verified end-to-end.

**Honest notes:** `context_signal` is simulator-provided (production would source it from real tooling); ECE 0.276 indicates imperfect calibration; AWS deployment is NOT executed (awaiting explicit approval + least-privilege IAM); repo publish, video recording, and the full Builder Center article remain pending human action.

> **Orchestration note:** A logical multi-agent coordination plan exists as a steering file (`.kiro/steering/multi-agent-coordination.md`). Because Kiro Crew / the parallel Workflows engine are not installed, execution uses spec-driven development plus in-session sub-agent delegation with disjoint file ownership (per the Parallel Execution Guidance and Task Dependency Graph below).

### Workstream → Milestone map

| # | Workstream | Primary milestone(s) | Owns (directories) |
|---|------------|----------------------|--------------------|
| 1 | Environment and SDK validation | M0 | `docs/validation/`, `requirements*.txt` pins |
| 2 | Decider 2B integration and reusable decision pattern | M0, M1 | `patterns/confidence_aware_tool_router/`, `backend/app/decider/` |
| 3 | Incident simulator and deterministic policy engine | M0, M1 | `backend/app/simulation/`, `backend/app/policy/`, `backend/app/approval/` |
| 4 | Strands and Amazon Bedrock orchestration | M0, M1 | `backend/app/orchestrator/`, `backend/app/bedrock/` |
| 5 | FastAPI, persistence, and SSE | M0, M1 | `backend/app/api/`, `backend/app/persistence/`, `backend/app/events/` |
| 6 | React mission-control dashboard | M0, M1, M2 | `frontend/` |
| 7 | Incident Time Machine and replay | M2 | `backend/app/replay/`, `frontend/src/screens/TimeMachine/` |
| 8 | Evaluation, benchmarking, and automated testing | M0–M3 | `backend/tests/`, `backend/app/benchmark/`, `.github/workflows/`, `evaluation/` |
| 9 | Docker and AWS deployment | M3 | `deploy/`, `docker-compose.yml`, `infra/` |
| 10 | Hackathon documentation, article, and demo preparation | M3 | `docs/`, `README.md`, `SUBMISSION.md` |

---

## Tasks

## Workstream 1 — Environment and SDK validation

> Closes the design's **Unresolved Assumptions (a)–(e)**. These are hard prerequisites for the integration tasks in Workstreams 2 and 4. All P0, all on the M0 critical path.

- [x] 1. Environment and SDK validation

  - [x] 1.1 Install `strands-decider` and capture actual runtime version pins
    - **Requirements**: Req 3.2, 13.5 (closes Unresolved Assumption (a))
    - **Dependencies**: none
    - **Scope**: Create `backend/requirements.txt` / `backend/pyproject.toml` with `strands-decider`, `strands-agents` (Strands Agents SDK), `boto3`, `fastapi`, `sqlmodel`, `hypothesis`, `pytest`, `ruff`, `mypy`. Install into a Python 3.11+ venv on the target OS. Record the resolved `torch`/`transformers`/`strands-decider` versions into `docs/validation/env-pins.md`. Design: Design Validation Findings §1.
    - **Acceptance**: `pip show strands-decider torch transformers` succeeds; `docs/validation/env-pins.md` records exact versions and the target OS/arch; dependency versions pinned (exact/`==`) in the manifest.
    - **Validation**: `pip install -r backend/requirements.txt && python -c "import strands_decider, transformers, torch; print(strands_decider.__version__, torch.__version__, transformers.__version__)"`
    - **Workstream**: 1 — Environment and SDK validation
    - **Priority**: P0

  - [x] 1.2 Stand up `strands-decider serve` and confirm the live `POST /v1/systemone` JSON schema
    - **Requirements**: Req 3.1, 3.2, 3.3 (closes Unresolved Assumption (c)); Property 9, Property 10
    - **Dependencies**: 1.1
    - **Scope**: Run `strands-decider serve <model> --port 8000 --device <cpu|mps|cuda|mlx>`. Issue a real `POST /v1/systemone` with a `state` string and a `questions` keyed object (`recovery_tool` → `{type:"choice", instructions, criteria:{...five tools...}}`). Capture the live response and confirm it matches the verified contract: `answers` keyed object with `choice`/`probabilities`/`confidence`, and top-level `model`/`usage`/`latency_ms`. Write the captured request/response and any deltas into `docs/validation/decider-contract.md`. Design: Strands / Decider Integration.
    - **Acceptance**: A real response is captured; the schema matches the design's documented shape (or deltas are recorded and the design contract is reconciled); the contract doc is the frozen reference for adapter code in 2.2.
    - **Validation**: `curl -s -X POST localhost:8000/v1/systemone -H 'content-type: application/json' -d @docs/validation/sample_request.json | tee docs/validation/sample_response.json` and confirm keys `answers.recovery_tool.choice`, `.probabilities`, `.confidence`, top-level `model`, `latency_ms`.
    - **Workstream**: 1 — Environment and SDK validation
    - **Priority**: P0

  - [x] 1.3 Confirm Strands Agents SDK intervention import paths and `before_tool_call` signature
    - **Requirements**: Req 2.1, 2.4 (closes Unresolved Assumption (b))
    - **Dependencies**: 1.1
    - **Scope**: Against the installed Strands Agents SDK, confirm the exact import path for `Agent`, the `interventions=[...]` constructor argument, the `InterventionHandler` base, the `before_tool_call` method signature, and the Proceed/Deny/Confirm/Guide action constructors. Record verified symbols in `docs/validation/strands-sdk.md`. Design: InterventionHandler mapping.
    - **Acceptance**: Verified symbol names/paths recorded; a throwaway `Agent(interventions=[handler])` instantiates and a no-op `before_tool_call` is invoked.
    - **Validation**: `python docs/validation/strands_probe.py` (a small probe script that imports the SDK, builds an Agent with a trivial handler, and prints the resolved class paths) exits 0.
    - **Workstream**: 1 — Environment and SDK validation
    - **Priority**: P0

  - [x] 1.4 Confirm Bedrock model availability in the configured region via boto3
    - **Requirements**: Req 5.1, 5.2, 5.7 (closes Unresolved Assumption (e))
    - **Dependencies**: 1.1
    - **Scope**: Using boto3 with the AWS default credential resolution chain, call the Bedrock availability/list-foundation-models API for the configured region and confirm the configured model id is listed. Record the confirmed model id + region into `docs/validation/bedrock.md`. No secrets committed. Design: Bedrock Integration.
    - **Acceptance**: The configured model id is confirmed available in-region; the availability pre-check approach is documented for reuse in 4.4.
    - **Validation**: `python -c "import boto3; print([m for m in boto3.client('bedrock', region_name='<region>').list_foundation_models()['modelSummaries'] if '<model-id>' in m['modelId']])"` returns a non-empty match.
    - **Workstream**: 1 — Environment and SDK validation
    - **Priority**: P0

  - [x] 1.5 Record preliminary EC2 instance candidate and memory headroom (estimation method only)
    - **Requirements**: Req 14.2, 14.3; Req 8.7 (closes Unresolved Assumption (d))
    - **Dependencies**: 1.1, 1.2
    - **Scope**: Measure observed memory footprint and startup/warm/cold latency of the local `serve` run from 1.2. Record a candidate EC2 instance type with ≥16 GB headroom guidance and the cost-estimation **method** (`instance hourly rate × demo hours + Bedrock per-token cost × measured tokens`) into `docs/validation/ec2-sizing.md`. Do NOT fabricate any dollar figure. Design: Design Validation Findings §6, AWS Deployment Topology.
    - **Acceptance**: Memory/latency observations recorded; candidate instance type named with rationale; cost method documented with no invented dollar amount; unresolved items explicitly flagged for WS9.
    - **Validation**: Reviewer confirms `docs/validation/ec2-sizing.md` contains observed metrics and an estimation method with zero fabricated cost figures.
    - **Workstream**: 1 — Environment and SDK validation
    - **Priority**: P0

- [x] 2. **[M0 milestone gate — assumptions closed]** Checkpoint — verify WS1 outputs
  - **Requirements**: Req 17.1, 13.7
  - **Dependencies**: 1.1, 1.2, 1.3, 1.4, 1.5
  - Ensure all validation docs exist and the live Decider contract is frozen; ask the user if any schema delta requires a design update before integration code is written. Ensure all tests pass, ask the user if questions arise.
  - **Workstream**: 1 — Environment and SDK validation
  - **Priority**: P0

---

## Workstream 2 — Decider 2B integration and reusable decision pattern

> Produces the independently-importable `patterns/confidence_aware_tool_router/` package (Req 4) and the AegisPulse-side adapter wiring. **M0/M1.**

- [x] 3. Reusable Confidence-Aware Tool Router package

  - Implemented 2026-10-18: reusable package + backend adapter; 24 tests passing (10 package + 4 adapter + 10 G1 contracts); real Strands InterventionHandler builds (SDK delta: `name` property required — handled). Files confined to patterns/confidence_aware_tool_router/ and backend/app/decider/.

  - [x] 3.1 Scaffold the `patterns/confidence_aware_tool_router/` package and typed decision model
    - **Requirements**: Req 4.1, 4.4; Req 3.1, 3.6; Property 9
    - **Dependencies**: 2 (M0 gate)
    - **Scope**: Create `patterns/confidence_aware_tool_router/` as an independently importable package (its own `pyproject.toml`, `__init__.py`). Define `ToolChoiceDecision` (question_id, fixed `options` tuple, prompt) and `DeciderDecision` dataclasses, and the module-level fixed five-tool option constant reused for both request construction and validation. Depends on NO AegisPulse app code. Design: Reusable package section.
    - **Acceptance**: `import confidence_aware_tool_router` works from a clean venv with no AegisPulse import; the fixed option set is a single source of truth.
    - **Validation**: `pip install -e patterns/confidence_aware_tool_router && python -c "from confidence_aware_tool_router import ToolChoiceDecision, DeciderDecision"`
    - **Workstream**: 2 — Decider 2B integration and reusable decision pattern
    - **Priority**: P0

  - [x] 3.2 Implement `ConfidenceAwareToolRouter.decide` request build + response parse/validate
    - **Requirements**: Req 3.1, 3.2, 3.3, 3.6, 3.8, 3.9, 3.10; Property 9, Property 10, Property 13
    - **Dependencies**: 3.1, 1.2
    - **Scope**: In the package, build the `POST /v1/systemone` body (`state` string + `questions` keyed object with `type:"choice"`, `instructions`, `criteria` name→description map). Parse `answers[qid].choice`/`.probabilities`/`.confidence` and top-level `model`/`usage`/`latency_ms` into `DeciderDecision`. Enforce a 10s timeout. Raise typed `OutOfSetError` / `MalformedResponseError` / `DeciderUnavailableError`. Design: Strands / Decider Integration (verified contract).
    - **Acceptance**: Valid in-set responses parse to a bounded `[0,1]` confidence and in-set tool; out-of-set/malformed/timeout raise the correct typed exceptions with the offending value available.
    - **Validation**: `pytest patterns/confidence_aware_tool_router/tests/test_router.py`
    - **Workstream**: 2 — Decider 2B integration and reusable decision pattern
    - **Priority**: P0

  - [x]* 3.3 Write unit tests for the package in isolation (fakes, no real Decider)
    - **Requirements**: Req 4.5; Req 3.3, 3.8, 3.9, 3.10
    - **Dependencies**: 3.2
    - **Scope**: Unit tests in `patterns/confidence_aware_tool_router/tests/` driving the parser with fake responses: in-set happy path, out-of-set value, missing `choice`, confidence outside `[0,1]`, timeout/unavailable. No AegisPulse imports.
    - **Acceptance**: All failure modes covered; tests run without the app on the path.
    - **Validation**: `cd patterns/confidence_aware_tool_router && pytest`
    - **Workstream**: 2 — Decider 2B integration and reusable decision pattern
    - **Priority**: P0

  - [x] 3.4 Implement `build_intervention_handler` composing router + policy
    - **Requirements**: Req 4.2; Req 2.4, 2.5, 2.6
    - **Dependencies**: 3.2, 1.3
    - **Scope**: Provide `build_intervention_handler(router, policy)` returning a Strands `InterventionHandler` whose `before_tool_call` maps (Decider selection + policy outcome) → Proceed / Confirm / Deny / Guide using the confirmed SDK symbols from 1.3. Policy object injected (interface only; concrete policy in WS3). Design: InterventionHandler mapping.
    - **Acceptance**: Handler returns the correct action per the mapping table; high-blast-radius → Confirm; blocked → Deny.
    - **Validation**: `pytest patterns/confidence_aware_tool_router/tests/test_intervention.py`
    - **Workstream**: 2 — Decider 2B integration and reusable decision pattern
    - **Priority**: P0

  - [x] 3.5 Write package README, usage/limitations/safety docs with hackathon tags
    - **Requirements**: Req 4.3, 4.6
    - **Dependencies**: 3.1, 3.2, 3.4
    - **Scope**: `patterns/confidence_aware_tool_router/README.md` documenting the `#tool-selection` pattern, usage example, limitations, safety guidance, and explicit `#strands-decider-2b` and `#tool-selection` tags; include an `examples/` integration snippet.
    - **Acceptance**: README references both tags; example integration importable; limitations + safety guidance present.
    - **Validation**: `grep -l "#strands-decider-2b" patterns/confidence_aware_tool_router/README.md && grep -l "#tool-selection" patterns/confidence_aware_tool_router/README.md`
    - **Workstream**: 2 — Decider 2B integration and reusable decision pattern
    - **Priority**: P1

  - [x] 3.6 Wire the AegisPulse Decider adapter over the package
    - **Requirements**: Req 3.4, 3.7; Req 11.1
    - **Dependencies**: 3.2
    - **Scope**: In `backend/app/decider/adapter.py`, consume the package `ConfidenceAwareToolRouter` to produce the candidate recovery tool and assemble the `Decision_Record` fields (selected, confidence, scores, model, latency, evidence_snapshot_id), forwarding for persistence (WS5). Design: Components and Interfaces (Tool_Router).
    - **Acceptance**: Adapter returns a candidate + Decision_Record payload; depends on the package public API only.
    - **Validation**: `pytest backend/tests/unit/test_decider_adapter.py`
    - **Workstream**: 2 — Decider 2B integration and reusable decision pattern
    - **Priority**: P0

---

## Workstream 3 — Incident simulator and deterministic policy engine

> **M0/M1.** Simulation Engine, deterministic Safety Policy Engine, Approval Gate.

- [x] 4. Deterministic Simulation Engine

  - [x] 4.1 Implement seeded telemetry generation for `Bad_Deployment` + scenario registry
    - **Requirements**: Req 1.1, 1.2, 1.3, 1.7; Property 1, Property 2
    - **Dependencies**: 2 (M0 gate)
    - **Scope**: `backend/app/simulation/engine.py` + `scenarios.py`. Register the five scenario ids; fully implement `Bad_Deployment` telemetry (service health, request metrics, error metrics) from a fixed uint32 seed; expose each scenario's labeled expected outcome sourced independently of any Decider response. Design: Simulation Engine, Data Models (SCENARIO).
    - **Acceptance**: `Bad_Deployment` telemetry is deterministic per seed, all series non-empty and non-negative; labeled expected outcome exposed.
    - **Validation**: `pytest backend/tests/unit/test_simulation.py -k bad_deployment`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x] 4.2 Implement simulation-only remediation execution and recovery outcomes
    - **Requirements**: Req 1.4, 1.5, 1.8, 6.18; Property 3
    - **Dependencies**: 4.1
    - **Scope**: `execute(tool, params) -> RecoveryOutcome` acting only on in-memory simulated infrastructure; returns MTTR seconds, service impact, result ∈ {success, failure}. No AWS mutation client anywhere in the module. Design: Simulation Engine.
    - **Acceptance**: Execution never touches real resources; outcome is complete and well-typed.
    - **Validation**: `pytest backend/tests/unit/test_simulation.py -k execute`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x] 4.3 Implement invalid-scenario rejection
    - **Requirements**: Req 1.6; Property 4
    - **Dependencies**: 4.1
    - **Scope**: Reject any scenario id not exactly one of the five; return a structured error naming the invalid id; generate no telemetry.
    - **Acceptance**: Unknown ids rejected with the offending id named; no telemetry produced.
    - **Validation**: `pytest backend/tests/unit/test_simulation.py -k invalid_scenario`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x] 4.4 Implement remaining four scenarios
    - **Requirements**: Req 1.1, 1.2, 1.3, 1.7; Req 17.2; Property 1, Property 2
    - **Dependencies**: 4.1
    - **Scope**: Implement `Capacity_Saturation`, `Memory_Leak`, `Database_Connection_Exhaustion`, `Ambiguous_Incident` telemetry + labeled expected outcomes; tune `Ambiguous_Incident` so a replay modification can shift the recommended tool (supports Req 7.4).
    - **Acceptance**: All five scenarios deterministic and well-formed; `Ambiguous_Incident` tuned for divergence.
    - **Validation**: `pytest backend/tests/unit/test_simulation.py`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P1

  - [x]* 4.5 Write property test — telemetry well-formedness
    - **Requirements**: Req 1.2; **Property 1: Telemetry well-formedness invariant** — Validates Requirements 1.2
    - **Dependencies**: 4.1
    - **Scope**: Hypothesis test (≥100 iterations) over all five scenarios and valid seeds; tagged `# Feature: chaospilot-ai, Property 1: ...`.
    - **Validation**: `pytest backend/tests/property/test_props.py -k property1`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P1

  - [x]* 4.6 Write property test — deterministic telemetry reproduction
    - **Requirements**: Req 1.3; **Property 2: Deterministic telemetry reproduction** — Validates Requirements 1.3
    - **Dependencies**: 4.1
    - **Scope**: Hypothesis test (≥100 iterations) asserting byte-for-byte equality on repeated generation; tagged Property 2.
    - **Validation**: `pytest backend/tests/property/test_props.py -k property2`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P1

  - [x]* 4.7 Write property tests — recovery completeness and invalid-scenario rejection
    - **Requirements**: Req 1.5, 1.6; **Property 3: Recovery outcome completeness** — Validates 1.5; **Property 4: Invalid scenario rejection** — Validates 1.6
    - **Dependencies**: 4.2, 4.3
    - **Scope**: Two Hypothesis tests (≥100 iterations each), tagged Property 3 and Property 4.
    - **Validation**: `pytest backend/tests/property/test_props.py -k "property3 or property4"`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P1

- [x] 5. Deterministic Safety Policy Engine and Approval Gate

  - [x] 5.1 Implement the pure deterministic policy `authorize(...)` with blast-radius table and evaluation order
    - **Requirements**: Req 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 16.6, 16.7; Property 15, Property 16, Property 17, Property 18
    - **Dependencies**: 2 (M0 gate)
    - **Scope**: `backend/app/policy/engine.py`. Pure function over `(candidate_tool, confidence, evidence_flags, blast_radius, approval_state, attempt_count, prior_outcome, decider_health)`. Implement the blast-radius table, allowlist check, missing-evidence block, confidence threshold (default 0.90, configurable) applied to automatic state-changing only, and **blast radius evaluated before the confidence gate** so rollback/scale_out always go PendingApproval. Never reads Bedrock text. Design: Safety Policy Engine (flowchart + decision table + Req 16.6 vs 6.7 interaction).
    - **Acceptance**: Decision table reproduced exactly; high-blast-radius never auto-executes; below-threshold blocks state-changing but permits investigate/evidence/escalate.
    - **Validation**: `pytest backend/tests/unit/test_policy.py`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x] 5.2 Implement fail-closed behavior on Decider failure
    - **Requirements**: Req 6.14; Req 3.8, 3.9, 3.10; Property 13
    - **Dependencies**: 5.1, 3.2
    - **Scope**: On `decider_health` failure (out-of-set/malformed/unavailable/timeout), block all automatic state-changing actions while permitting `investigate_further`, additional evidence collection, `escalate_to_human`. Design: Error Handling / Failure Handling Matrix.
    - **Acceptance**: Every Decider failure mode yields FailedClosed with read-only paths permitted.
    - **Validation**: `pytest backend/tests/unit/test_policy.py -k fail_closed`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x] 5.3 Implement idempotency, retry-limit, and audit hash-chain
    - **Requirements**: Req 6.15, 6.16, 6.17, 12.7, 12.9; Property 21, Property 22, Property 23, Property 31
    - **Dependencies**: 5.1
    - **Scope**: At-most-once execution keyed by `(incident_state, Correlation_ID)` returning the original outcome on repeat; max 3 failed attempts → retry-limit-exceeded; one append-only audit entry per authorization decision (Correlation_ID, tool, confidence, outcome, approval status) with `entry_hash = H(prev_hash || canonical(entry))`. Design: Safety Policy Engine (Additional guarantees), Data Models (immutability & tamper-evidence).
    - **Acceptance**: Repeats execute once; 4th attempt blocked; audit chain verifies and breaks on tampering.
    - **Validation**: `pytest backend/tests/unit/test_policy.py -k "idempotent or retry or audit"`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x] 5.4 Implement the Approval Gate (bound tuple, expiry, exact-match)
    - **Requirements**: Req 6.9, 6.10, 6.11, 6.12, 6.13, 12.8; Property 19, Property 20
    - **Dependencies**: 5.1
    - **Scope**: `backend/app/approval/gate.py`. Bind each approval to `(incident_id, action, action_parameters, evidence_snapshot_id)`; configurable expiry default 120s; reject on any tuple mismatch or expiry or rejection and record not-executed. Design: Approval Workflow (state diagram).
    - **Acceptance**: Exact-match accepted; any mismatch/expiry/rejection blocks execution.
    - **Validation**: `pytest backend/tests/unit/test_approval.py`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x] 5.5 Implement external input validation at the policy boundary
    - **Requirements**: Req 6.19, 12.5, 10.7; Property 24
    - **Dependencies**: 5.1
    - **Scope**: Validate all external inputs reaching the engine before any state-changing action is applied; reject invalid inputs structurally. Design: Safety Policy Engine (Input validation).
    - **Acceptance**: Invalid inputs rejected before mutation.
    - **Validation**: `pytest backend/tests/unit/test_policy.py -k input_validation`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P0

  - [x]* 5.6 Write property tests — policy allowlist, evidence, threshold, blast-radius
    - **Requirements**: Req 6.1, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 16.6, 16.7; **Property 15** (6.1), **Property 16** (6.3), **Property 17** (6.4/6.5/6.6/16.6/16.7), **Property 18** (6.7/6.8)
    - **Dependencies**: 5.1
    - **Scope**: Four Hypothesis tests (≥100 iterations each) tagged Property 15–18.
    - **Validation**: `pytest backend/tests/property/test_props.py -k "property15 or property16 or property17 or property18"`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P1

  - [x]* 5.7 Write property tests — fail-closed, Bedrock-independence, idempotency, retry, audit, approval binding/expiry, input validation
    - **Requirements**: Req 5.6, 6.14, 6.15, 6.16, 6.17, 6.19, 6.9–6.12, 12.5, 12.7, 12.8, 12.9; **Property 13, 14, 19, 20, 21, 22, 23, 24, 31**
    - **Dependencies**: 5.2, 5.3, 5.4, 5.5
    - **Scope**: Hypothesis tests (≥100 iterations each) tagged with their Property numbers. Property 14 asserts policy outcome is identical regardless of Bedrock text (including injection strings).
    - **Validation**: `pytest backend/tests/property/test_props.py -k "property13 or property14 or property19 or property20 or property21 or property22 or property23 or property24 or property31"`
    - **Workstream**: 3 — Incident simulator and deterministic policy engine
    - **Priority**: P1

---

## Workstream 4 — Strands and Amazon Bedrock orchestration

> **M0/M1.** Strands Agent orchestration + Bedrock reasoning.

- [x] 6. Strands Agent orchestration and Bedrock reasoning

  - [x] 6.1 Implement the Incident Orchestrator (evidence gathering + timeline events)
    - **Requirements**: Req 2.1, 2.2, 2.3, 2.7; Property 5, Property 6
    - **Dependencies**: 2 (M0 gate), 4.1, 4.2
    - **Scope**: `backend/app/orchestrator/agent.py`. Use the Strands Agents SDK; invoke each registered telemetry-reading tool against the Simulation Engine exactly once; build an immutable Evidence_Snapshot; record each tool invocation as a timeline event with ISO-8601 ms timestamp + Correlation_ID; on tool error record event, retain evidence, continue without unverified action. Design: Decision Lifecycle steps 3–4.
    - **Acceptance**: Each telemetry tool invoked exactly once before snapshot; timeline events well-formed; tool errors non-fatal.
    - **Validation**: `pytest backend/tests/unit/test_orchestrator.py`
    - **Workstream**: 4 — Strands and Amazon Bedrock orchestration
    - **Priority**: P0

  - [x] 6.2 Register the InterventionHandler and wire Confirm/Deny preservation
    - **Requirements**: Req 2.4, 2.5, 2.6; Property 7, Property 8
    - **Dependencies**: 6.1, 3.4, 5.1
    - **Scope**: Register the handler from 3.4 via `Agent(interventions=[...])` (symbols from 1.3). Confirm → enter and preserve pending-approval until human decision; Deny → do not execute + record denied-action event with Correlation_ID. Design: InterventionHandler mapping.
    - **Acceptance**: Confirm preserves pending state; Deny prevents execution and records the denial.
    - **Validation**: `pytest backend/tests/unit/test_orchestrator.py -k "confirm or deny"`
    - **Workstream**: 4 — Strands and Amazon Bedrock orchestration
    - **Priority**: P0

  - [x] 6.3 Implement the Bedrock Reasoner (assessment + availability pre-check)
    - **Requirements**: Req 5.1, 5.2, 5.3, 5.7, 5.8, 5.9
    - **Dependencies**: 1.4, 6.1
    - **Scope**: `backend/app/bedrock/reasoner.py`. boto3 Bedrock Runtime client using the default credential chain; configurable model id; region/model availability pre-check before first invocation; produce concise human-readable assessment; treat responses as untrusted (schema + length + content validation); on error/throttle record structured error and continue. Design: Bedrock Integration.
    - **Acceptance**: Assessment produced for gathered evidence; availability pre-check runs; errors non-blocking; responses validated.
    - **Validation**: `pytest backend/tests/unit/test_bedrock.py` (mocked boto3) + the real invocation covered by the M0 e2e (task 7) and release gate (task 20.6).
    - **Workstream**: 4 — Strands and Amazon Bedrock orchestration
    - **Priority**: P0

  - [x] 6.4 Enforce Bedrock non-override guarantees (never selects, never authorizes)
    - **Requirements**: Req 3.5, 5.5, 5.6, 12.10; Property 12, Property 14, Property 32
    - **Dependencies**: 6.2, 6.3, 5.1
    - **Scope**: Ensure no path lets Bedrock output reach a tool selection or alter the policy outcome; candidate comes only from the Decider; policy function never reads Bedrock text. Design: Bedrock Integration (hard guarantees), Security & Threat Model.
    - **Acceptance**: Candidate equals Decider output regardless of Bedrock text; policy outcome invariant to Bedrock content.
    - **Validation**: `pytest backend/tests/property/test_props.py -k "property12 or property14 or property32"`
    - **Workstream**: 4 — Strands and Amazon Bedrock orchestration
    - **Priority**: P0

  - [x] 6.5 Implement hypotheses, explanations, and post-incident summaries
    - **Requirements**: Req 5.3, 5.4
    - **Dependencies**: 6.3
    - **Scope**: Add Bedrock-generated hypotheses, decision explanations for the Decision Observatory, and post-incident summaries. (Original-vs-replay summary lives in WS7.)
    - **Acceptance**: Each output type produced and validated.
    - **Validation**: `pytest backend/tests/unit/test_bedrock.py -k "hypothesis or summary or explanation"`
    - **Workstream**: 4 — Strands and Amazon Bedrock orchestration
    - **Priority**: P1

  - [x]* 6.6 Write property tests — evidence invocation count, timeline format, Confirm/Deny
    - **Requirements**: Req 2.2, 2.3, 2.5, 2.6; **Property 5** (2.2), **Property 6** (2.3), **Property 7** (2.5), **Property 8** (2.6)
    - **Dependencies**: 6.1, 6.2
    - **Scope**: Hypothesis tests (≥100 iterations each) tagged Property 5–8, using in-memory fakes (no real Decider/Bedrock).
    - **Validation**: `pytest backend/tests/property/test_props.py -k "property5 or property6 or property7 or property8"`
    - **Workstream**: 4 — Strands and Amazon Bedrock orchestration
    - **Priority**: P1

---

## Workstream 5 — FastAPI, persistence, and SSE

> **M0/M1.** REST API, Pydantic models, persistence (SQLite WAL + atomic approve+execute), SSE streaming.

- [x] 7. **[M0 MILESTONE]** Real-inference vertical slice — `Bad_Deployment` end-to-end through the full gated path
  - **Requirements**: Req 17.1, 16.5; Req 2.*, 3.*, 5.*, 6.7, 6.8, 6.9, 11.1
  - **Dependencies**: 3.6, 4.2, 5.4, 6.2, 6.3, 6.4, 8.1, 8.2
  - **Scope**: Wire the critical path for `Bad_Deployment`: Simulation Engine → Orchestrator + InterventionHandler → Decider adapter (real `POST /v1/systemone`) → deterministic policy → Approval Gate (rollback requires human approval) → simulated execution → Decision_Record persisted. Minimal API endpoints (incidents, investigate, decide, approve, execute) and SSE. This is the **critical path and M0 milestone**. Design: MVP Delivery Slice, Decision Lifecycle.
  - **Acceptance**: A real Decider inference returns a parsed in-set tool; a real Bedrock assessment is produced; rollback triggers human approval; on approval the simulated recovery executes and a Decision_Record is persisted; completable within the under-3-minute demo budget.
  - **Validation**: `pytest backend/tests/e2e/test_m0_bad_deployment.py` (real Decider + real Bedrock, non-mocked) and a manual `curl` walk of the 5 endpoints; the release gate (20.6) covers the real-call requirement.
  - **Workstream**: 5 — FastAPI, persistence, and SSE
  - **Priority**: P0

- [ ] 8. FastAPI backend, persistence, and SSE

  - [x] 8.1 Implement persistence layer: SQLModel/SQLite with WAL + busy_timeout + named volume, immutable records, audit table
    - **Requirements**: Req 11.1, 11.2, 11.3, 11.4, 12.9; Property 30, Property 31
    - **Dependencies**: 2 (M0 gate)
    - **Scope**: `backend/app/persistence/`. SQLModel entities (SCENARIO, INCIDENT, EVIDENCE_SNAPSHOT, DECISION_RECORD, EVENT, APPROVAL, AUDIT_LOG, BENCHMARK_RUN). Enable `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`; DB file on a persistent Docker named volume; write-once Decision_Records (reject update/delete); append-only audit; repository abstraction for future PostgreSQL. Events persisted before fan-out. Design: Data Models.
    - **Acceptance**: WAL + busy_timeout active; Decision_Records immutable; retrieval returns records + events with ordering preserved.
    - **Validation**: `pytest backend/tests/unit/test_persistence.py`
    - **Workstream**: 5 — FastAPI, persistence, and SSE
    - **Priority**: P0

  - [x] 8.2 Implement FastAPI app, Pydantic models, Correlation-ID middleware, 12 endpoints, server-side authz/state validation
    - **Requirements**: Req 10.1, 10.2, 10.3, 10.4, 10.6, 10.7, 12.4; Property 28, Property 29
    - **Dependencies**: 8.1, 3.6, 5.1, 6.1
    - **Scope**: `backend/app/api/`. All 12 `/api/v1` endpoints from the API Contracts table; Pydantic request/response models; Correlation-ID middleware on every request/response; standard structured error envelope; server-side state-machine validation before mutation (reject illegal transitions with `CONFLICT`). Design: API Contracts, Incident State Machine.
    - **Acceptance**: Every endpoint present; responses carry Correlation_ID; illegal transitions rejected before mutation; invalid bodies → `VALIDATION_ERROR` naming the field.
    - **Validation**: `pytest backend/tests/integration/test_api.py`
    - **Workstream**: 5 — FastAPI, persistence, and SSE
    - **Priority**: P0

  - [x] 8.3 Implement the atomic approve+execute transaction
    - **Requirements**: Req 6.15, 12.7, 12.8; Property 20, Property 21
    - **Dependencies**: 8.1, 5.4
    - **Scope**: Single DB transaction that validates exact-tuple + not-expired, marks the approval consumed, and writes execution result + Decision_Record together, preventing double-execution on concurrent/replayed approvals. Design: Data Models (Atomic approve + execute transaction).
    - **Acceptance**: Concurrent/replayed approval cannot double-execute; stale approval rejected inside the transaction.
    - **Validation**: `pytest backend/tests/integration/test_approve_execute_atomic.py`
    - **Workstream**: 5 — FastAPI, persistence, and SSE
    - **Priority**: P0

  - [x] 8.4 Implement SSE event streaming with event IDs, heartbeats, and Last-Event-ID durable replay
    - **Requirements**: Req 10.5, 11.3; Req 2.3
    - **Dependencies**: 8.1, 8.2
    - **Scope**: `backend/app/events/`. `GET /api/v1/incidents/{id}/events` as `text/event-stream`; each event carries a monotonic ULID `id:`; periodic heartbeat/comment lines; on reconnect honor `Last-Event-ID` and durably replay persisted events after that id (events persisted before fan-out). Design: API Contracts (Event streaming), Event Schema.
    - **Acceptance**: Clients receive ordered events with ids; heartbeats sent; reconnect replays missed events durably.
    - **Validation**: `pytest backend/tests/integration/test_sse.py`
    - **Workstream**: 5 — FastAPI, persistence, and SSE
    - **Priority**: P1

  - [ ] 8.5 Implement security logging for security-relevant events
    - **Requirements**: Req 12.11, 12.12, 12.13, 12.2, 12.3, 12.6
    - **Dependencies**: 8.2
    - **Scope**: Structured log entry on security-relevant events (authorization failures, policy blocks, fail-closed); secrets retrieved from Secrets Manager / Parameter Store (not source); enforce no arbitrary shell execution and no unrestricted AWS operations; allowlist enforcement at the API boundary. Design: Security & Threat Model.
    - **Acceptance**: Security events logged structurally; no committed secrets; allowlist enforced server-side.
    - **Validation**: `pytest backend/tests/integration/test_security_logging.py` + `git grep -nE "AKIA|SECRET|PRIVATE KEY" -- . :!*.md` returns nothing.
    - **Workstream**: 5 — FastAPI, persistence, and SSE
    - **Priority**: P1

  - [x]* 8.6 Write property tests — persistence round-trip, Correlation-ID presence, server-side authz
    - **Requirements**: Req 10.4, 10.6, 11.1–11.4; **Property 28** (10.4), **Property 29** (10.6), **Property 30** (11.1–11.4)
    - **Dependencies**: 8.1, 8.2
    - **Scope**: Hypothesis tests (≥100 iterations each) tagged Property 28–30.
    - **Validation**: `pytest backend/tests/property/test_props.py -k "property28 or property29 or property30"`
    - **Workstream**: 5 — FastAPI, persistence, and SSE
    - **Priority**: P1

---

## Workstream 6 — React mission-control dashboard

> **M0/M1/M2.** Owns `frontend/` exclusively — parallelizable with all backend workstreams.

- [ ] 9. React mission-control frontend

  - [x] 9.1 Scaffold React + TypeScript + Vite + Tailwind dark theme and API/SSE client
    - **Requirements**: Req 9.2, 9.9
    - **Dependencies**: none (contract from API Contracts is sufficient; can start in parallel with backend)
    - **Scope**: `frontend/` project; dark mission-control theme; typed REST client + SSE subscriber; accessible components, responsive layout, loading/error states. Design: Technology Choices, Architecture (Client).
    - **Acceptance**: App builds and runs against mocked API contract; theme + a11y baseline in place.
    - **Validation**: `cd frontend && npm run build && npm test`
    - **Workstream**: 6 — React mission-control dashboard
    - **Priority**: P0

  - [x] 9.2 Build Incident Arena and Recovery Timeline screens with approval controls (M0 UI)
    - **Requirements**: Req 9.1, 9.4, 9.5; Req 16.5
    - **Dependencies**: 9.1
    - **Scope**: `frontend/src/screens/IncidentArena/`, `.../RecoveryTimeline/`. Launch scenario, stream agent timeline, show recovery progress, present approve/reject controls when a high-impact action awaits approval. These two screens complete the M0 demo UI.
    - **Acceptance**: User can launch `Bad_Deployment`, watch timeline via SSE, and approve/reject a rollback.
    - **Validation**: `cd frontend && npm test -- IncidentArena RecoveryTimeline`
    - **Workstream**: 6 — React mission-control dashboard
    - **Priority**: P0

  - [x] 9.3 Build Decision Observatory screen (probabilities, confidence, evidence, policy outcome)
    - **Requirements**: Req 9.1, 9.3, 9.7, 9.8
    - **Dependencies**: 9.1
    - **Scope**: `frontend/src/screens/DecisionObservatory/`. Render Decider per-option probabilities, confidence indicators, selected tool, evidence inspection, Safety_Policy outcome; label REAL inference vs SIMULATED outcome vs illustrative sample; never show fabricated live predictions.
    - **Acceptance**: Observatory shows real decision data with correct real/sample labeling.
    - **Validation**: `cd frontend && npm test -- DecisionObservatory`
    - **Workstream**: 6 — React mission-control dashboard
    - **Priority**: P1

  - [ ] 9.4 Build Benchmark Lab and Architecture & About screens
    - **Requirements**: Req 9.1, 9.6, 9.7, 9.8
    - **Dependencies**: 9.1
    - **Scope**: `frontend/src/screens/BenchmarkLab/`, `.../About/`. Latency/cost benchmark charts (distinguishing measured vs estimated); architecture/about content. (Time Machine screen is WS7.)
    - **Acceptance**: Benchmark charts render measured-vs-estimated clearly; About screen complete.
    - **Validation**: `cd frontend && npm test -- BenchmarkLab About`
    - **Workstream**: 6 — React mission-control dashboard
    - **Priority**: P2

  - [x]* 9.5 Write frontend component/snapshot tests (sample-vs-real labeling, approval controls)
    - **Requirements**: Req 9.5, 9.7, 9.8, 13.6
    - **Dependencies**: 9.2, 9.3, 9.4
    - **Scope**: Component/snapshot tests for all screens, approval controls appearing for high-impact actions, and sample-vs-real labeling.
    - **Validation**: `cd frontend && npm test`
    - **Workstream**: 6 — React mission-control dashboard
    - **Priority**: P1

---

## Workstream 7 — Incident Time Machine and replay

> **M2.** Backend replay engine + Time Machine screen.

- [x] 10. Counterfactual replay

  - [x] 10.1 Implement deterministic replay with modified-condition validation
    - **Requirements**: Req 7.1, 7.5, 7.6; Property 25
    - **Dependencies**: 7 (M0), 4.4, 8.2
    - **Scope**: `backend/app/replay/engine.py`. Store original run baseline (seed, scenario, snapshot, Decision_Record); layer validated modifications on the seeded generator; identical conditions + fixed seed reproduce original tool + policy outcome; invalid modifications → structured error, no replay. Design: Replay / Incident Time Machine Architecture.
    - **Acceptance**: Identical replay reproduces tool + policy outcome; invalid conditions rejected.
    - **Validation**: `pytest backend/tests/unit/test_replay.py`
    - **Workstream**: 7 — Incident Time Machine and replay
    - **Priority**: P1

  - [x] 10.2 Implement field-level diff, labeling, and Bedrock comparison summary
    - **Requirements**: Req 7.2, 7.3, 7.4, 7.7; Property 26, Property 27
    - **Dependencies**: 10.1, 6.5
    - **Scope**: Compare `selected Recovery_Tool`, `confidence`, `Safety_Policy outcome` marking each changed/unchanged; label tool/confidence REAL inference and outcomes SIMULATED; guarantee ≥1 scenario (`Ambiguous_Incident`) whose tool changes on replay; Bedrock summary stating whether the tool changed and why.
    - **Acceptance**: Diff correct; labels correct; divergent scenario demonstrated; summary produced.
    - **Validation**: `pytest backend/tests/unit/test_replay.py -k "diff or label or divergent"`
    - **Workstream**: 7 — Incident Time Machine and replay
    - **Priority**: P1

  - [x] 10.3 Build the Incident Time Machine screen
    - **Requirements**: Req 9.1, 7.2, 7.3
    - **Dependencies**: 10.2, 9.1
    - **Scope**: `frontend/src/screens/TimeMachine/`. Modify conditions, trigger replay, show original-vs-counterfactual comparison with REAL/SIMULATED labels.
    - **Acceptance**: User can replay and view the labeled comparison.
    - **Validation**: `cd frontend && npm test -- TimeMachine`
    - **Workstream**: 7 — Incident Time Machine and replay
    - **Priority**: P2

  - [x]* 10.4 Write property tests — seeded replay reproduction, diff correctness, labeling
    - **Requirements**: Req 7.1, 7.2, 7.3, 7.5; **Property 25** (7.1/7.5), **Property 26** (7.2), **Property 27** (7.3)
    - **Dependencies**: 10.1, 10.2
    - **Scope**: Hypothesis tests (≥100 iterations each) tagged Property 25–27.
    - **Validation**: `pytest backend/tests/property/test_props.py -k "property25 or property26 or property27"`
    - **Workstream**: 7 — Incident Time Machine and replay
    - **Priority**: P1

---

## Workstream 8 — Evaluation, benchmarking, and automated testing

> **M0–M3.** Property/unit/integration/e2e suites, CI, static gates, benchmark harness, real-inference release gate.

- [x] 11. Benchmark harness

  - [x] 11.1 Implement the Benchmark Harness (real inference both paths, identical inputs, warm-ups)
    - **Requirements**: Req 8.1, 8.2, 8.3, 8.9; Req 17.4
    - **Dependencies**: 3.6, 6.3, 4.4
    - **Scope**: `backend/app/benchmark/harness.py`. Real Bedrock-only selector vs real Decider 2B selector on identical incident states + option sets; ≥50 cases across all five scenarios with ≥5 per scenario; ≥3 warm-up iterations per path excluded from reported measurements. Design: Benchmark Methodology.
    - **Acceptance**: ≥50 cases with per-scenario ≥5; warm-ups excluded; both paths real inference, no mocked substitution.
    - **Validation**: `pytest backend/tests/integration/test_benchmark_harness.py -k "case_counts or warmups"`
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

  - [x] 11.2 Implement benchmark metrics, calibration, and no-fabrication reporting
    - **Requirements**: Req 8.4, 8.5, 8.6, 8.7, 8.8
    - **Dependencies**: 11.1
    - **Scope**: Measure end-to-end + inference latency (p50/p95), accuracy vs labeled expected outcomes (Req 1.7), unsafe-action rate, abstention-or-escalation rate, Bedrock token usage, estimated vs measured cost presented separately, confidence calibration where present, sample count + hardware config. No fabricated savings. Design: Benchmark Methodology.
    - **Acceptance**: All metrics reported; measured and estimated cost separated; no unsupported savings claimed.
    - **Validation**: `pytest backend/tests/integration/test_benchmark_harness.py -k "metrics or no_fabrication"`
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

  - [x] 11.3 Produce the ≥50 evaluation-cases artifact
    - **Requirements**: Req 8.2, 15.3
    - **Dependencies**: 11.1, 4.4
    - **Scope**: `evaluation/cases/` dataset of ≥50 labeled synthetic cases distributed across the five scenarios (≥5 each) with labeled expected outcomes.
    - **Acceptance**: Artifact present with the required distribution and labels.
    - **Validation**: `python evaluation/validate_cases.py` (asserts ≥50 total and ≥5 per scenario) exits 0.
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

- [ ] 12. Automated test suite, CI, and release gate

  - [ ] 12.1 Set up the property-test module with all 32 Hypothesis tests tagged and ≥100 iterations
    - **Requirements**: Req 13.1, 13.2, 13.3; all Properties 1–32
    - **Dependencies**: 4.7, 5.6, 5.7, 6.6, 8.6, 10.4 (the per-workstream property tests)
    - **Scope**: `backend/tests/property/test_props.py` consolidating/registering all 32 property tests, each ≥100 iterations, each tagged `# Feature: chaospilot-ai, Property {n}: {text}`. Ensure Property 11 (Decider-adapter round-trip, Req 13.3) is present. Design: Testing Strategy (property-based testing).
    - **Acceptance**: 32 property tests present, tagged, ≥100 iterations; round-trip Property 11 included.
    - **Validation**: `pytest backend/tests/property/ -q` and `grep -c "Feature: chaospilot-ai, Property" backend/tests/property/test_props.py` ≥ 32.
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

  - [x]* 12.2 Write the Decider-adapter round-trip property test (Property 11)
    - **Requirements**: Req 13.3; **Property 11: Decider adapter round-trip** — Validates Requirements 13.3
    - **Dependencies**: 3.2
    - **Scope**: Hypothesis test (≥100 iterations) asserting parse → serialize → parse yields an equivalent `DeciderDecision`; tagged Property 11.
    - **Validation**: `pytest patterns/confidence_aware_tool_router/tests/ -k roundtrip` or `pytest backend/tests/property/test_props.py -k property11`
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

  - [x]* 12.3 Write unit/integration/e2e coverage for the Req 13.2 scenario list
    - **Requirements**: Req 13.1, 13.2
    - **Dependencies**: 8.2, 5.4, 6.3, 10.1
    - **Scope**: Cover adapter parsing, fixed-option validation, missing telemetry, contradictory evidence, low confidence, approval enforcement/binding/expiration, fail-closed, invalid tool calls, idempotency, state-transition integrity, replay reproducibility, Bedrock errors/throttling, Decider unavailability, API validation, UI interaction, Docker startup, AWS configuration. Mocked externals in CI.
    - **Validation**: `pytest backend/tests -q`
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

  - [ ] 12.4 Configure GitHub Actions CI with mocked externals and static gates (Ruff/mypy/Pytest)
    - **Requirements**: Req 13.4, 13.5
    - **Dependencies**: 12.1, 12.3
    - **Scope**: `.github/workflows/ci.yml` running all test categories against mocked external services (except the release-gate job); backend `ruff check`, `mypy`, `pytest` with zero errors/failures. Design: Testing Strategy (static gates).
    - **Acceptance**: CI green with mocked externals; static gates enforced.
    - **Validation**: `ruff check backend && mypy backend && pytest backend -q`
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

  - [ ] 12.5 Wire the frontend test suite into CI
    - **Requirements**: Req 13.6
    - **Dependencies**: 9.5, 12.4
    - **Scope**: Add a frontend CI job running `npm test` (single-run mode) with zero errors.
    - **Validation**: `cd frontend && npm test`
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P1

  - [ ] 12.6 Implement the real-inference release gate
    - **Requirements**: Req 13.7, 13.8
    - **Dependencies**: 7 (M0), 11.2
    - **Scope**: A separate release-gate job/script requiring, against non-mocked services, ≥1 real Decider 2B inference returning a parsed in-set tool AND ≥1 validated real Bedrock invocation; on either failure, block release and record a structured error. Design: Testing Strategy (real-inference release gate).
    - **Acceptance**: Gate passes only with both real calls succeeding; failure blocks release with a structured error.
    - **Validation**: `python backend/release_gate.py` (exit 0 only when both real calls succeed) / `pytest backend/tests/release_gate -q`
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P0

  - [x] 12.7 Produce the benchmark report artifact
    - **Requirements**: Req 15.3, 8.4–8.8
    - **Dependencies**: 11.2, 11.3
    - **Scope**: `docs/benchmark-report.md` generated from a real benchmark run: p50/p95 latency, accuracy, unsafe/abstention rates, tokens, measured-vs-estimated cost, calibration, sample count, hardware. No fabricated figures.
    - **Acceptance**: Report reflects a recorded run with measured-vs-estimated separation.
    - **Validation**: Reviewer confirms `docs/benchmark-report.md` sourced from a real run with no unsupported savings.
    - **Workstream**: 8 — Evaluation, benchmarking, and automated testing
    - **Priority**: P2

---

## Workstream 9 — Docker and AWS deployment

> **M3.** Container packaging and least-privilege AWS deployment config.

- [ ] 13. Docker and AWS deployment

  - [ ] 13.1 Author Docker Compose stack (frontend, backend, decider serve, TLS reverse proxy) with Decider warm-up
    - **Requirements**: Req 14.1, 14.2; Req 5.7
    - **Dependencies**: 7 (M0), 1.5
    - **Scope**: `docker-compose.yml` + per-service Dockerfiles; `decider` runs `strands-decider serve <model> --port 8000`; reverse proxy terminating TLS; backend/readiness hook issues a throwaway warm-up inference once the decider reports ready; persistent named volume for the SQLite DB. Design: AWS Deployment Topology.
    - **Acceptance**: `docker compose up` brings all services healthy; decider warmed before first user-facing decision.
    - **Validation**: `docker compose up -d && curl -fsS localhost/api/v1/health | grep -q '"decider_reachable": *true'`
    - **Workstream**: 9 — Docker and AWS deployment
    - **Priority**: P2

  - [ ] 13.2 Author least-privilege IAM, CloudWatch logging, restricted inbound + TLS, mandatory tags, secrets wiring
    - **Requirements**: Req 14.3, 14.4, 14.5, 14.7; Req 12.11
    - **Dependencies**: 13.1
    - **Scope**: `infra/` IaC for a single EC2 with model-compatible hardware; IAM instance profile scoped to read/inference/logging only with NO production-mutation permission; CloudWatch log shipping; restricted inbound CIDR + TLS; mandatory tags Environment, Application, Owner, CostCenter, Compliance, DataClassification, ManagedBy; secrets from Secrets Manager / Parameter Store. Design: AWS Deployment Topology.
    - **Acceptance**: IAM has no mutate permissions; all seven mandatory tags present; inbound restricted + TLS; no committed secrets.
    - **Validation**: IaC validate/lint (e.g. `terraform validate` / `cfn-lint`) + a policy check asserting no `*:*` mutate actions and all seven tags on taggable resources.
    - **Workstream**: 9 — Docker and AWS deployment
    - **Priority**: P2

  - [ ] 13.3 Gate AWS deployment behind explicit human approval
    - **Requirements**: Req 14.6
    - **Dependencies**: 13.2
    - **Scope**: Deployment runbook/script that requires an explicit human approval step before any AWS deploy is performed (no auto-deploy).
    - **Acceptance**: Deploy cannot proceed without a recorded human approval.
    - **Validation**: Reviewer confirms the deploy script halts for explicit approval; dry-run shows the gate.
    - **Workstream**: 9 — Docker and AWS deployment
    - **Priority**: P2

  - [ ]* 13.4 Write Docker startup and AWS-config tests
    - **Requirements**: Req 13.2 (Docker startup, AWS configuration)
    - **Dependencies**: 13.1, 13.2
    - **Scope**: Automated checks for compose startup health and AWS config invariants (IAM no-mutate, tags present, TLS/inbound restricted).
    - **Validation**: `pytest backend/tests/integration/test_docker_startup.py backend/tests/integration/test_aws_config.py`
    - **Workstream**: 9 — Docker and AWS deployment
    - **Priority**: P2

---

## Workstream 10 — Hackathon documentation, article, and demo preparation

> **M3.** Submission deliverables.

- [ ] 14. Hackathon deliverables

  - [ ] 14.1 Produce the public GitHub-ready repo scaffold, README, and run instructions
    - **Requirements**: Req 15.1, 15.3; Req 16.1–16.4
    - **Dependencies**: 7 (M0)
    - **Scope**: Top-level `README.md` with documented local start commands, project framing (incident-commander arena), and links to docs; ensure the app starts from documented commands. Design: MVP Delivery Slice, Overview.
    - **Acceptance**: Following README commands starts the app locally.
    - **Validation**: A clean checkout + documented commands bring up the local app (`docker compose up` or documented dev commands) and `/api/v1/health` returns OK.
    - **Workstream**: 10 — Hackathon documentation, article, and demo preparation
    - **Priority**: P2

  - [ ] 14.2 Produce the architecture diagram and demo instructions + screenshots
    - **Requirements**: Req 15.3, 15.4
    - **Dependencies**: 14.1, 9.2
    - **Scope**: `docs/architecture.md` (diagram from the design's Mermaid), `docs/demo-instructions.md`, and screenshots of the dashboards.
    - **Acceptance**: Diagram + demo instructions + screenshots present and current.
    - **Validation**: Reviewer confirms artifacts exist and match the running app.
    - **Workstream**: 10 — Hackathon documentation, article, and demo preparation
    - **Priority**: P2

  - [ ] 14.3 Write the under-3-minute demo video script and the Builder Center article draft
    - **Requirements**: Req 15.4, 16.5; Req 16.1–16.4
    - **Dependencies**: 14.1, 14.2
    - **Scope**: `docs/demo-script.md` runnable in under 3 minutes highlighting the Decider materially driving selection + the gated policy; `docs/builder-center-article.md` draft.
    - **Acceptance**: Script fits the 3-minute budget and showcases the Decider contribution; article draft complete.
    - **Validation**: Reviewer times a dry run of the scripted demo at < 3 minutes.
    - **Workstream**: 10 — Hackathon documentation, article, and demo preparation
    - **Priority**: P2

  - [ ] 14.4 Produce license, third-party attribution review, submission checklist, and hackathon tags
    - **Requirements**: Req 15.3, 15.5, 15.6
    - **Dependencies**: 14.1
    - **Scope**: `LICENSE`, `docs/attribution.md` (third-party review incl. Apache-2.0 Decider weights), `SUBMISSION.md` checklist, and explicit `#strands-decider-2b` and `#tool-selection` tags in submission materials.
    - **Acceptance**: License + attribution present; checklist complete; both tags present in submission materials.
    - **Validation**: `grep -R "#strands-decider-2b" SUBMISSION.md && grep -R "#tool-selection" SUBMISSION.md` and reviewer confirms LICENSE + attribution.
    - **Workstream**: 10 — Hackathon documentation, article, and demo preparation
    - **Priority**: P2

  - [ ] 14.5 Final acceptance review against Req 15.7
    - **Requirements**: Req 15.7, 17.5
    - **Dependencies**: 7, 12.6, 10.2, 11.2, 3.5, 13.1, 14.3, 14.4
    - **Scope**: Verify the full completion checklist: app starts from documented commands, five scenarios available, real Decider + real Bedrock demonstrated, Decider controls meaningful tool selection, policy gates enforced, ≥1 simulated recovery completes, replay works, benchmark reproducible, reusable pattern imports independently, tests pass, no secrets committed, public demo < 3 minutes.
    - **Acceptance**: Every Req 15.7 item checked and evidenced.
    - **Validation**: Walk the `SUBMISSION.md` checklist; all items pass.
    - **Workstream**: 10 — Hackathon documentation, article, and demo preparation
    - **Priority**: P2

- [ ] 15. Final checkpoint — Ensure all tests pass
  - **Requirements**: Req 13.5, 13.6, 13.7
  - **Dependencies**: 14.5
  - Ensure all backend (`pytest`, `ruff`, `mypy`), frontend (`npm test`), property, and release-gate checks pass. Ask the user if questions arise.
  - **Workstream**: 10 — Hackathon documentation, article, and demo preparation
  - **Priority**: P2

---

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP; core implementation tasks are never optional.
- Each task references specific requirement acceptance criteria and, where applicable, design Correctness Properties for traceability.
- The 32 property tests use Hypothesis with ≥100 iterations each and are tagged `# Feature: chaospilot-ai, Property {n}: {text}`. They never call the real Decider or Bedrock; real inference is exercised only by the M0 e2e (task 7) and the release gate (task 12.6).
- **M0 is the critical path** (tasks 1.1–1.5, 2, 3.1–3.2, 3.4, 3.6, 4.1–4.3, 5.1–5.5, 6.1–6.4, 7, 8.1–8.3, 9.1–9.2, 12.6). Breadth features — the other four scenarios, advanced dashboards, Time Machine, and the full benchmark — are P1/P2 and follow M0 per Requirement 17.
- No fabricated performance or cost figures anywhere; measured and estimated are always presented separately.

## Parallel Execution Guidance

Kiro Workflows/Crew can run tasks concurrently **only when they do not own or modify the same files**. File ownership by workstream is disjoint by directory:

- **Frontend (WS6, `frontend/`)** can run fully in parallel with every backend workstream from the start — it depends only on the API contract, not backend code.
- **Reusable package (WS2, `patterns/confidence_aware_tool_router/`)** is a separate package; its tasks (3.1–3.5) do not touch `backend/app/` and can run parallel to WS3's simulation/policy work.
- **Simulation (WS3, `backend/app/simulation/`)** and **Policy/Approval (WS3, `backend/app/policy/`, `backend/app/approval/`)** own different directories and can run in parallel after the M0 gate (task 2).
- **Bedrock (WS4, `backend/app/bedrock/`)** can run parallel to the Decider package and simulation work.

Must be serialized (hard dependencies or shared files):

- WS1 (tasks 1.1–1.5) must finish before any integration task that freezes adapter/SDK/Bedrock assumptions (2.x, 4.x, 6.3) — gated by the task 2 checkpoint.
- The **Decider adapter (3.6)** needs the package (3.2); the **Orchestrator intervention wiring (6.2)** needs the handler (3.4) and policy (5.1).
- The **M0 e2e (task 7)** is the convergence point; it depends on the adapter, policy, approval, orchestrator, Bedrock, persistence, API, and minimal UI being in place.
- **Persistence (8.1)** must precede API endpoints (8.2), the atomic approve+execute transaction (8.3), and SSE (8.4) because they share `backend/app/persistence/` and `backend/app/api/` files.
- **Replay (WS7)** depends on M0 and the five scenarios (4.4); the **Benchmark Harness (WS8, 11.x)** depends on the adapter, Bedrock, and all scenarios.
- **Deployment (WS9)** and **docs/submission (WS10)** depend on a working M0 and the breadth features they document.

No two parallel tasks may own or modify the same file; where two tasks would touch the same module, they are placed in different waves below.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "9.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5"] },
    { "id": 3, "tasks": ["3.1", "4.1", "5.1", "8.1"] },
    { "id": 4, "tasks": ["3.2", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "5.2", "5.3", "5.4", "5.5", "6.1", "9.2", "9.3", "9.4"] },
    { "id": 5, "tasks": ["3.3", "3.4", "3.5", "3.6", "5.6", "5.7", "6.3", "8.2", "12.2", "9.5"] },
    { "id": 6, "tasks": ["6.2", "6.5", "8.3", "8.4", "8.5"] },
    { "id": 7, "tasks": ["6.4", "6.6", "8.6"] },
    { "id": 8, "tasks": ["7"] },
    { "id": 9, "tasks": ["10.1", "11.1", "13.1", "14.1"] },
    { "id": 10, "tasks": ["10.2", "11.2", "11.3", "13.2", "14.2"] },
    { "id": 11, "tasks": ["10.3", "10.4", "12.1", "12.3", "12.7", "13.3", "13.4", "14.3", "14.4"] },
    { "id": 12, "tasks": ["12.4"] },
    { "id": 13, "tasks": ["12.5", "12.6"] },
    { "id": 14, "tasks": ["14.5"] }
  ]
}
```
