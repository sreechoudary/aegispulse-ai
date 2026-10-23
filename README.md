# AegisPulse AI - Detect. Decide. Defend.

An autonomous incident commander built on **real Strands Decider 2B** + **Amazon Bedrock**, with a
**deterministic safety policy** and **human approval** for high-impact actions. Built for the
October 2026 AWS Strands Decider 2B Agent Experience Hackathon.

**#strands-decider-2b  #tool-selection**

## What it does
Launch a synthetic production incident, watch a Strands agent gather telemetry, let Amazon Bedrock
assess root cause, let **Strands Decider 2B** select the recovery tool with calibrated confidence,
let a **separate deterministic policy** authorize or block it, require **human approval** for
high-blast-radius remediation, execute against a **simulated** environment, and replay
counterfactually in the **Incident Time Machine**.

> Architectural thesis: **The Decider SELECTS. The policy AUTHORIZES. Bedrock EXPLAINS.
> Nothing overrides the one before it.** All remediation is simulation-only; no real AWS mutation.

## Architecture (high level)
- **Reusable pattern**: `patterns/confidence_aware_tool_router/` - independently importable
  `#tool-selection` package wrapping the real Decider `POST /v1/systemone` contract.
- **Backend**: Python 3.12 / FastAPI / Pydantic / SQLite(SQLModel, WAL) / SSE.
  `app/decider` (adapter), `app/simulation`, `app/policy` + `app/approval`, `app/bedrock`,
  `app/api`, `app/replay`, `app/runtime` (lifecycle + reliability), `app/benchmark`.
- **Frontend**: React + TypeScript + Vite + Tailwind mission-control dashboard.
- **Contracts**: frozen in `backend/app/contracts/` (see `docs/contracts/G1_CONTRACTS.md`).

## Quickstart (local)
1. Python env: `uv venv .venv --python 3.12 && VIRTUAL_ENV=.venv uv pip install -r backend/requirements... `
   (strands-decider 0.1.0, strands-agents 1.61.1, torch 2.14.1, transformers 5.20.1, fastapi, sqlmodel).
2. Start the Decider server (see `docs/DEMO_SCRIPT.md` pre-flight).
3. AWS: `aws sso login --profile ar-dev`; export `AWS_PROFILE=ar-dev AWS_REGION=us-east-1`.
4. Backend: run the FastAPI app (`app.api.app:build_app`). Frontend: `cd frontend && npm install && npm run dev`.

## Tests
- Backend: `cd backend && PYTHONPATH=. pytest` (unit, contract, property-based, integration).
- Frontend: `cd frontend && npm test`.
- Lint/type: `ruff check app`, `mypy app/...`.

## Benchmarks
See `evaluation/BENCHMARK_REPORT.md` (honest methodology audit + equal-context results) and
`evaluation/benchmark_final_live.json`. 50-case sample; no statistical-superiority claims.

## Safety
- No real AWS mutation: the only AWS call is Bedrock `converse` (inference). No create/delete/update APIs.
- High-blast-radius actions (rollback, scale-out) always require human approval regardless of confidence.
- Fail-closed on any Decider failure; deterministic policy never reads model text (prompt-injection safe).

## License & attribution
Apache-2.0 (matches strands-decider / strands-agents). Third-party attribution review: see NOTICE (TODO before publish).
