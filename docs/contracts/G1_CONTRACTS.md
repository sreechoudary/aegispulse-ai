# AegisPulse AI — G1 Frozen Interface Contracts

**Status: FROZEN (G1 passed 2026-10-18, 10/10 contract tests green).**
**Authoritative source of truth:** `backend/app/contracts/` (enums.py, schemas.py, protocols.py).
This document is the human-readable mirror. Code wins if they ever diverge.

> No Wave A component may redefine these shared contracts. Changes require Lead
> Architect approval and a G1 re-freeze (re-run `pytest backend/tests/unit/test_contracts_g1.py`).

## 1. Decider adapter interface
- Request (`DeciderRequest`): `{state: str, questions: {<id>: {type:"choice", instructions, criteria:{tool:desc}}}}` — `questions` is a KEYED OBJECT.
- Raw response (`DeciderRawResponse`): `{model, answers:{<id>:{type,choice,probabilities,confidence}}, usage:{input_tokens,output_tokens}, latency_ms}`.
- Normalized (`DeciderDecision`): selected (in `FIXED_OPTION_SET`), confidence in [0,1], scores (from probabilities), model_version, latency_ms, evidence_snapshot_id.
- Option set (`FIXED_OPTION_SET`): rollback_deployment, scale_out_service, restart_unhealthy_tasks, investigate_further, escalate_to_human.
- Timeout: 10s (`DECIDER_TIMEOUT_SECONDS`). Failures raise `OutOfSetError` / `MalformedResponseError` / `DeciderUnavailableError`.
- Acceptance: valid in-set parse succeeds; out-of-set/confidence>1/missing-field raise; 10s timeout -> unavailable.

## 2. Policy engine `authorize(PolicyInput) -> PolicyDecision`
- Input (deterministic, NO Bedrock text): candidate_tool, confidence, evidence_present, approval_status, attempt_count, decider_health, confidence_threshold(=0.90).
- Output: outcome (AutoAuthorized|PendingApproval|Blocked|FailedClosed), reason, blast_radius, requires_approval, may_execute.
- Rules: allowlist; missing-evidence blocks; blast radius evaluated BEFORE confidence gate (rollback/scale_out always PendingApproval); below-threshold blocks state-changing but permits investigate/escalate; decider_health!=healthy -> FailedClosed; max 3 attempts.
- Acceptance: decision table in design.md reproduced exactly; pure function of input.

## 3. DecisionRecord & EvidenceSnapshot
- `EvidenceSnapshot` (immutable): id, incident_id, correlation_id, created_at(ISO-8601 ms), telemetry_summary, evidence_refs.
- `DecisionRecord` (immutable, Req 11.1): captures input_state, evidence_references, typed_question, available_options, selected_option, confidence, per_option_scores, model_version, inference_latency_ms, policy_outcome, approval_status, execution_result.

## 4. Incident lifecycle & approval transitions
- States (`IncidentState`): Created→Simulating→Investigating→Assessing→Deciding→{PolicyEvaluated|FailedClosed}→{AutoAuthorized|PendingApproval|Blocked}→Executing→{Recovered|RecoveryFailed}; Replaying.
- `ALLOWED_TRANSITIONS` is the frozen table; server rejects illegal transitions (Req 10.6).
- Approval (`ApprovalBinding`, `ApprovalStatus`): bound to (incident_id, action, action_parameters, evidence_snapshot_id); expiry default 120s; mismatch/expiry/reject -> not executed.

## 5. FastAPI request/response contracts
- 12 endpoints per design API Contracts. All bodies Pydantic; all responses carry a correlation_id; failures use `ApiErrorResponse`.

## 6. SSE event envelope & types
- `EventEnvelope`: event_id(ULID, used as SSE id), correlation_id, incident_id, timestamp(ISO-8601 ms), type(`EventType`), payload.
- Event types enumerated in `EventType` (incl. heartbeat for SSE keepalive).

## 7. Error codes & correlation IDs
- `ErrorCode`: VALIDATION_ERROR, NOT_FOUND, CONFLICT, FAIL_CLOSED, APPROVAL_INVALID, UPSTREAM_UNAVAILABLE.
- Every request/response carries a correlation_id.

## InterventionAction note (M0 finding)
strands-agents 1.61.1 `before_tool_call(self, event: BeforeToolCallEvent, **kwargs) -> Proceed | Deny | Guide | Confirm | Transform`. `Transform` exists beyond the 4 originally designed; handler receives a typed event object.


---

## Strands SDK Compatibility Findings (preserved — Wave A)

Verified against `strands-agents==1.61.1` (regression-tested in
`backend/tests/unit/test_strands_sdk_compat.py`):

1. **`InterventionHandler` requires a `name` property.** It is an abstract member;
   a handler subclass that omits it cannot be instantiated. Our reusable handler
   implements `name` ("confidence_aware_recovery_tool_router").
2. **Actions:** `strands.interventions` exposes `Proceed, Deny, Confirm, Guide, Transform`.
   `Transform` exists beyond the originally-designed four — available but unused by us.
3. **`before_tool_call(self, event, **kwargs)`** receives a typed `BeforeToolCallEvent`
   (a lifecycle event object), NOT loose tool/args. Return type is the union
   `Proceed | Deny | Guide | Confirm | Transform` (or an awaitable of it).
4. **`Agent(interventions=[...])`** accepts the handler list via the `interventions` kwarg.

Regression tests fail loudly if a future SDK upgrade changes any of the above.
