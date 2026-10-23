---
inclusion: manual
---
# AegisPulse AI — Multi-Agent Coordination Plan

> **Orchestration reality:** Kiro Crew and a parallel "Workflows" engine are NOT installed in this
> environment (verified 2026-10-18). This document models the eight engineering roles *logically*.
> Execution uses Kiro Spec-Driven Development as the source of truth, `tasks.md` as the authoritative
> tracker, and **in-session sub-agent delegation** for independent workstreams. We never claim multiple
> agents are running concurrently unless actual delegation occurs.

## Source of truth & controls

- **Specs** (`requirements.md`, `design.md`, `tasks.md`) are authoritative. Changes go through the spec, not ad hoc.
- **`tasks.md`** tracks all implementation work and status.
- **File-ownership rule:** no two concurrently-delegated tasks may own/modify the same file or directory.
- **Integration gates:** cross-cutting merges happen only at the named gates below, owned by the Lead Architect role.

## Eight engineering roles

| Role | Responsibilities | Owns (directories/files) | Key deps | Acceptance |
|------|------------------|--------------------------|----------|------------|
| **Lead Architect** | Architecture governance, shared interfaces, dependency order, integration gates, merges | `design.md`, `tasks.md`, shared type/interface stubs, `.kiro/steering/*` | — | Interfaces frozen before dependents start; gates pass; traceability intact |
| **Decider Engineer** | Decider 2B integration + reusable `#tool-selection` pattern | `patterns/confidence_aware_tool_router/`, `backend/app/decider/` | Shared interfaces | Real in-set selection; package importable + tested in isolation (Req 3, 4) |
| **AI Engineer** | Bedrock reasoning + Strands agent orchestration | `backend/app/orchestrator/`, `backend/app/bedrock/` | Decider adapter iface, policy iface | Real Bedrock assessment; InterventionHandler wired; Bedrock never overrides (Req 2, 5) |
| **SRE Engineer** | Incident simulator, deterministic policy, approval gate | `backend/app/simulation/`, `backend/app/policy/`, `backend/app/approval/` | Shared interfaces | Deterministic sim; policy decision table exact; fail-closed; approval binding (Req 1, 6) |
| **Backend Engineer** | FastAPI, SQLite/SQLModel, SSE | `backend/app/api/`, `backend/app/persistence/`, `backend/app/events/` | API contracts, Decision_Record schema | Endpoints per contract; WAL+volume; SSE ids/heartbeat/replay (Req 10, 11) |
| **Frontend Engineer** | React dashboard + Incident Time Machine UI | `frontend/` | Approved API contracts only | Six screens; real-vs-sample labels; a11y; tests green (Req 9) |
| **QA Engineer** | Tests, property-based suite, benchmarking, release gate | `backend/tests/`, `backend/app/benchmark/`, `.github/workflows/`, `evaluation/` | Components under test | 32 properties ≥100 iters; mocked CI; real-inference release gate (Req 8, 13) |
| **Release Engineer** | Docker, AWS deploy config, submission | `deploy/`, `docker-compose.yml`, `infra/`, `docs/`, `README.md`, `SUBMISSION.md` | Working app | Compose up; least-priv IAM; tags; TLS; deliverables + tags (Req 14, 15) |

## Integration gates (owned by Lead Architect)

- **G0 — M0 gate:** real Decider + real Bedrock + one gated recovery. ✅ PASSED (see M0 report).
- **G1 — Shared interfaces frozen:** Decider adapter API, policy `authorize(...)` signature, Decision_Record schema, API contracts, event schema. Must freeze before parallel workstreams start.
- **G2 — Vertical slice integrated:** one scenario end-to-end through FastAPI + persistence + SSE + minimal UI.
- **G3 — Breadth complete:** five scenarios, full policy/approval, core dashboards.
- **G4 — Replay + benchmark + full dashboards.**
- **G5 — Release:** deployment config, release gate (≥1 real Decider + ≥1 real Bedrock), docs, submission.

## File-ownership map (conflict-free parallelism)

Disjoint directory ownership lets these proceed in parallel after G1:
- Decider Engineer → `patterns/`, `backend/app/decider/`
- SRE Engineer → `backend/app/simulation/`, `backend/app/policy/`, `backend/app/approval/`
- Backend Engineer → `backend/app/api/`, `backend/app/persistence/`, `backend/app/events/`
- Frontend Engineer → `frontend/`
- QA Engineer → `backend/tests/`, `evaluation/`

Serialized (shared ownership or hard dep): anything touching shared interface stubs (Lead Architect), and AI Engineer's orchestrator which imports the Decider adapter + policy interfaces.
