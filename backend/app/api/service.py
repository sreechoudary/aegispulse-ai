"""
Incident service — orchestrates the gated flow over the frozen contracts.

Bedrock reasoner and Decider adapter are INJECTED so the service is testable without
real inference; the real-inference wiring happens in the API layer. Enforces server-side
state transitions (Req 10.6) and persists Decision_Records + events (Req 11).
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from app.approval import ApprovalGate
from app.contracts import (
    ALLOWED_TRANSITIONS,
    FIXED_OPTION_SET,
    ApprovalBinding,
    ApprovalStatus,
    DeciderDecision,
    DeciderHealth,
    DeciderUnavailableError,
    DecisionRecord,
    EventType,
    IncidentState,
    MalformedResponseError,
    OutOfSetError,
    PolicyInput,
    PolicyOutcome,
)
from app.events import iso_now, make_event
from app.persistence import Repository
from app.policy import PolicyEngine
from app.policy.audit import AuditLog, IdempotencyLedger
from app.simulation import InvalidScenarioError, SimulationEngine


class StateTransitionError(RuntimeError):
    pass


class IncidentService:
    def __init__(self, repo: Repository, decider: Any, approval: ApprovalGate,
                 bedrock_assess: Callable[[str], str] | None = None) -> None:
        self.repo = repo
        self.sim = SimulationEngine()
        self.policy = PolicyEngine()
        self.decider = decider
        self.approval = approval
        self.audit = AuditLog()
        self.ledger = IdempotencyLedger()
        self.bedrock_assess = bedrock_assess  # callable(state)->text, or None
        self._decider_decisions: dict[str, DeciderDecision] = {}
        self._assessments: dict[str, str] = {}

    # --- helpers ---
    def _emit(self, incident_id, cid, etype, payload):
        self.repo.append_event(make_event(incident_id, cid, etype, payload))

    def _transition(self, incident_id: str, to_state: IncidentState) -> None:
        inc = self.repo.get_incident(incident_id)
        if inc is None:
            raise StateTransitionError(f"unknown incident {incident_id}")
        cur = inc["state"]
        if to_state.value not in ALLOWED_TRANSITIONS.get(cur, frozenset()):
            raise StateTransitionError(f"illegal transition {cur} -> {to_state.value}")
        self.repo.set_state(incident_id, to_state.value)

    # --- flow ---
    def create(self, scenario_id: str, seed: int) -> dict[str, Any]:
        if scenario_id not in {s.scenario_id for s in self.sim.list_scenarios()}:
            raise InvalidScenarioError(scenario_id)
        incident_id = f"inc_{uuid.uuid4().hex[:12]}"
        cid = f"cid_{uuid.uuid4().hex[:12]}"
        self.repo.create_incident(incident_id=incident_id, scenario_id=scenario_id, seed=seed,
                                  state=IncidentState.CREATED.value, correlation_id=cid,
                                  created_at=iso_now())
        self.repo.set_state(incident_id, IncidentState.SIMULATING.value)
        telemetry = self.sim.generate(scenario_id, seed)
        self._emit(incident_id, cid, EventType.TELEMETRY_GENERATED,
                   {"scenario_id": scenario_id, "seed": seed, "health": telemetry["service_health"]})
        self.repo.set_state(incident_id, IncidentState.INVESTIGATING.value)
        return {"incident_id": incident_id, "correlation_id": cid, "state": IncidentState.INVESTIGATING.value,
                "telemetry": telemetry}

    def investigate(self, incident_id: str) -> dict[str, Any]:
        inc = self._req(incident_id)
        cid = inc["correlation_id"]
        telemetry = self.sim.generate(inc["scenario_id"], inc["seed"])
        for tool_name in ("read_health", "read_errors", "read_latency", "read_resources"):
            self._emit(incident_id, cid, EventType.TOOL_INVOKED, {"tool": tool_name})
        ev_id = f"ev_{uuid.uuid4().hex[:12]}"
        self._emit(incident_id, cid, EventType.EVIDENCE_SNAPSHOT_CREATED, {"evidence_snapshot_id": ev_id})
        self._transition(incident_id, IncidentState.ASSESSING)
        assessment = ""
        if self.bedrock_assess is not None:
            assessment = self.bedrock_assess(telemetry["summary"])
            self._emit(incident_id, cid, EventType.BEDROCK_ASSESSMENT, {"text": assessment[:300]})
        self._assessments[incident_id] = assessment
        return {"evidence_snapshot_id": ev_id, "assessment": assessment, "telemetry": telemetry}

    def decide(self, incident_id: str, evidence_snapshot_id: str) -> dict[str, Any]:
        inc = self._req(incident_id)
        cid = inc["correlation_id"]
        telemetry = self.sim.generate(inc["scenario_id"], inc["seed"])
        state_text = telemetry["summary"]
        if self._assessments.get(incident_id):
            state_text += " | assessment: " + self._assessments[incident_id]
        self._transition(incident_id, IncidentState.DECIDING)
        health = DeciderHealth.HEALTHY
        decision: DeciderDecision | None = None
        try:
            decision = self.decider.decide(state_text, evidence_snapshot_id, cid)
            self._decider_decisions[incident_id] = decision
            self._emit(incident_id, cid, EventType.DECIDER_DECISION,
                       {"selected": decision.selected, "confidence": decision.confidence,
                        "latency_ms": decision.latency_ms, "model": decision.model_version,
                        "scores": decision.scores})
        except OutOfSetError as e:
            health = DeciderHealth.OUT_OF_SET
            self._emit(incident_id, cid, EventType.DECIDER_ERROR, {"reason": "out_of_set", "value": e.returned_value})
        except MalformedResponseError:
            health = DeciderHealth.MALFORMED
            self._emit(incident_id, cid, EventType.DECIDER_ERROR, {"reason": "malformed"})
        except DeciderUnavailableError:
            health = DeciderHealth.UNAVAILABLE
            self._emit(incident_id, cid, EventType.DECIDER_ERROR, {"reason": "unavailable"})

        tool = decision.selected if decision else "investigate_further"
        conf = decision.confidence if decision else 0.0
        pol = self.policy.authorize(PolicyInput(
            candidate_tool=tool, confidence=conf, evidence_present=True,
            approval_status=ApprovalStatus.NONE, decider_health=health))
        self._emit(incident_id, cid, EventType.POLICY_EVALUATED,
                   {"outcome": pol.outcome.value, "reason": pol.reason, "tool": tool})
        self.audit.append({"cid": cid, "tool": tool, "confidence": conf,
                           "outcome": pol.outcome.value, "approval": "none"})
        if pol.outcome is PolicyOutcome.FAILED_CLOSED:
            self._transition(incident_id, IncidentState.FAILED_CLOSED)
        else:
            self._transition(incident_id, IncidentState.POLICY_EVALUATED)
            nxt = {PolicyOutcome.AUTO_AUTHORIZED: IncidentState.AUTO_AUTHORIZED,
                   PolicyOutcome.PENDING_APPROVAL: IncidentState.PENDING_APPROVAL,
                   PolicyOutcome.BLOCKED: IncidentState.BLOCKED}[pol.outcome]
            self._transition(incident_id, nxt)
            if pol.outcome is PolicyOutcome.PENDING_APPROVAL:
                binding = ApprovalBinding(incident_id=incident_id, action=tool,
                                          action_parameters={"scenario": inc["scenario_id"]},
                                          evidence_snapshot_id=evidence_snapshot_id)
                self.approval.request(binding)
                self._emit(incident_id, cid, EventType.APPROVAL_REQUESTED, {"action": tool})
        self._persist_decision(incident_id, cid, evidence_snapshot_id, decision, pol,
                               ApprovalStatus.NONE, None, telemetry)
        return {"selected": tool, "confidence": conf, "policy_outcome": pol.outcome.value,
                "requires_approval": pol.requires_approval, "decider_health": health.value,
                "expected_outcome": self.sim.expected_outcome(inc["scenario_id"]),
                "scores": decision.scores if decision else {},
                "latency_ms": decision.latency_ms if decision else None,
                "model": decision.model_version if decision else None,
                "assessment": self._assessments.get(incident_id, ""),
                "policy_reason": pol.reason}

    def approve(self, incident_id: str, action: str, evidence_snapshot_id: str, approve: bool) -> dict[str, Any]:
        inc = self._req(incident_id)
        cid = inc["correlation_id"]
        binding = ApprovalBinding(incident_id=incident_id, action=action,
                                  action_parameters={"scenario": inc["scenario_id"]},
                                  evidence_snapshot_id=evidence_snapshot_id)
        status = self.approval.resolve(binding, approve)
        etype = {ApprovalStatus.APPROVED: EventType.APPROVAL_GRANTED,
                 ApprovalStatus.REJECTED: EventType.APPROVAL_REJECTED,
                 ApprovalStatus.EXPIRED: EventType.APPROVAL_EXPIRED}[status]
        self._emit(incident_id, cid, etype, {"action": action})
        if status is ApprovalStatus.APPROVED:
            self._transition(incident_id, IncidentState.AUTO_AUTHORIZED)
        else:
            self._transition(incident_id, IncidentState.BLOCKED)
        return {"approval_status": status.value}

    def execute(self, incident_id: str) -> dict[str, Any]:
        inc = self._req(incident_id)
        cid = inc["correlation_id"]
        decision = self._decider_decisions.get(incident_id)
        tool = decision.selected if decision else "investigate_further"
        key = (f"{incident_id}:{inc['state']}", cid)
        prior = self.ledger.get(key)
        if prior is not None:
            return {"recovery": prior, "idempotent_replay": True}
        self._transition(incident_id, IncidentState.EXECUTING)
        outcome = self.sim.execute(tool, {"scenario": inc["scenario_id"]})
        rec = {"tool": outcome.tool, "mttr_seconds": outcome.mttr_seconds,
               "service_impact": outcome.service_impact, "result": outcome.result}
        self.ledger.put(key, rec)
        self._emit(incident_id, cid, EventType.ACTION_EXECUTED, {"tool": tool, "simulated": True})
        self._emit(incident_id, cid, EventType.RECOVERY_MEASURED, rec)
        self._transition(incident_id, IncidentState.RECOVERED if outcome.result == "success"
                         else IncidentState.RECOVERY_FAILED)
        return {"recovery": rec, "idempotent_replay": False}

    def replay(self, incident_id: str, conditions: dict[str, Any]) -> dict[str, Any]:
        """Counterfactual replay: re-run with modified conditions as a NEW incident.
        The original incident record is never mutated (Req 7)."""
        from app.replay import (
            apply_conditions,
            compare,
            validate_conditions,
        )
        orig = self._req(incident_id)
        validate_conditions(conditions)  # raises InvalidReplayConditionsError
        orig_decisions = self.repo.decisions_for(incident_id)
        if not orig_decisions:
            raise StateTransitionError("original incident has no decision to replay")
        orig_dr = orig_decisions[0]
        # build modified telemetry deterministically (same seed + conditions)
        base_tel = self.sim.generate(orig["scenario_id"], orig["seed"])
        mod_tel = apply_conditions(base_tel, conditions)
        # new incident for the replay (original left intact)
        replay = self.create(orig["scenario_id"], orig["seed"])
        rid = replay["incident_id"]
        self._emit(rid, replay["correlation_id"], EventType.REPLAY_STARTED,
                   {"original_incident_id": incident_id, "conditions": conditions})
        inv = self.investigate(rid)
        # inject modified telemetry context into the decide state via assessment slot
        self._assessments[rid] = (self._assessments.get(rid, "") + " | replay_conditions: "
                                  + mod_tel["summary"])
        dec = self.decide(rid, inv["evidence_snapshot_id"])
        replayed = {"selected": dec["selected"], "confidence": dec["confidence"],
                    "policy_outcome": dec["policy_outcome"]}
        original = {"selected": orig_dr["selected_option"], "confidence": orig_dr["confidence"],
                    "policy_outcome": orig_dr["policy_outcome"]}
        cmp = compare(original, replayed, incident_id, rid, conditions)
        self._emit(rid, replay["correlation_id"], EventType.REPLAY_COMPARED,
                   {"tool_changed": cmp.tool_changed})
        return {"original_incident_id": incident_id, "replay_incident_id": rid,
                "conditions": conditions, "tool_changed": cmp.tool_changed,
                "labels": {"decider": cmp.original_label, "recovery": cmp.outcome_label},
                "diffs": [{"field": d.field, "original": d.original, "replayed": d.replayed,
                           "changed": d.changed} for d in cmp.diffs]}

    def snapshot(self, incident_id: str) -> dict[str, Any]:
        inc = self._req(incident_id)
        return {"incident": inc, "events": self.repo.events_for(incident_id),
                "decisions": self.repo.decisions_for(incident_id)}

    def _persist_decision(self, incident_id, cid, ev_id, decision, pol, approval_status, exec_result, telemetry):
        rec = DecisionRecord(
            decision_record_id=f"dr_{uuid.uuid4().hex[:12]}", incident_id=incident_id,
            correlation_id=cid, evidence_snapshot_id=ev_id,
            input_state={"summary": telemetry["summary"]},
            evidence_references=[ev_id], typed_question={"id": "recovery_tool", "type": "choice"},
            available_options=list(FIXED_OPTION_SET),
            selected_option=decision.selected if decision else "investigate_further",
            confidence=decision.confidence if decision else 0.0,
            per_option_scores=decision.scores if decision else {},
            model_version=decision.model_version if decision else "n/a",
            inference_latency_ms=decision.latency_ms if decision else 0.0,
            policy_outcome=pol.outcome, approval_status=approval_status, execution_result=exec_result)
        self.repo.save_decision(rec.model_dump())

    def _req(self, incident_id: str) -> dict[str, Any]:
        inc = self.repo.get_incident(incident_id)
        if inc is None:
            raise StateTransitionError(f"unknown incident {incident_id}")
        return inc
