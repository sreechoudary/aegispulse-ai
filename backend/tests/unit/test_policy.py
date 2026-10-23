"""Policy engine + approval + audit tests (Req 6.*, 16.6/16.7)."""
from app.approval import ApprovalGate
from app.contracts import (
    ApprovalBinding,
    ApprovalStatus,
    DeciderHealth,
    PolicyInput,
    PolicyOutcome,
)
from app.policy import PolicyEngine
from app.policy.audit import AuditLog, IdempotencyLedger

P = PolicyEngine()

def _in(tool, conf=0.95, evidence=True, approval=ApprovalStatus.NONE, attempts=0,
        health=DeciderHealth.HEALTHY):
    return PolicyInput(candidate_tool=tool, confidence=conf, evidence_present=evidence,
                       approval_status=approval, attempt_count=attempts, decider_health=health)

def test_high_blast_always_pending_even_at_full_confidence():
    d = P.authorize(_in("rollback_deployment", conf=1.0))
    assert d.outcome is PolicyOutcome.PENDING_APPROVAL
    d2 = P.authorize(_in("scale_out_service", conf=1.0))
    assert d2.outcome is PolicyOutcome.PENDING_APPROVAL

def test_high_blast_approved_executes():
    d = P.authorize(_in("rollback_deployment", approval=ApprovalStatus.APPROVED))
    assert d.outcome is PolicyOutcome.AUTO_AUTHORIZED and d.may_execute

def test_high_blast_rejected_blocks():
    d = P.authorize(_in("rollback_deployment", approval=ApprovalStatus.REJECTED))
    assert d.outcome is PolicyOutcome.BLOCKED and not d.may_execute

def test_medium_blast_above_threshold_auto():
    assert P.authorize(_in("restart_unhealthy_tasks", conf=0.95)).outcome is PolicyOutcome.AUTO_AUTHORIZED

def test_medium_blast_below_threshold_blocked():
    assert P.authorize(_in("restart_unhealthy_tasks", conf=0.5)).outcome is PolicyOutcome.BLOCKED

def test_missing_evidence_blocks():
    assert P.authorize(_in("restart_unhealthy_tasks", evidence=False)).outcome is PolicyOutcome.BLOCKED

def test_non_state_changing_auto():
    assert P.authorize(_in("investigate_further", conf=0.1)).outcome is PolicyOutcome.AUTO_AUTHORIZED
    assert P.authorize(_in("escalate_to_human", conf=0.1)).outcome is PolicyOutcome.AUTO_AUTHORIZED

def test_fail_closed_on_unhealthy_decider_state_changing():
    d = P.authorize(_in("rollback_deployment", health=DeciderHealth.UNAVAILABLE))
    assert d.outcome is PolicyOutcome.FAILED_CLOSED and not d.may_execute

def test_fail_closed_permits_readonly():
    d = P.authorize(_in("investigate_further", health=DeciderHealth.MALFORMED))
    assert d.outcome is PolicyOutcome.AUTO_AUTHORIZED

def test_retry_limit_blocks():
    assert P.authorize(_in("restart_unhealthy_tasks", attempts=3)).outcome is PolicyOutcome.BLOCKED

# --- approval gate ---
def _bind(params=None):
    return ApprovalBinding(incident_id="i1", action="rollback_deployment",
                           action_parameters=params or {"v": "2.4.1"}, evidence_snapshot_id="ev1")

def test_approval_exact_match_approved():
    clock = [0.0]
    g = ApprovalGate(expiry_seconds=120, now=lambda: clock[0])
    g.request(_bind())
    assert g.resolve(_bind(), approve=True) is ApprovalStatus.APPROVED

def test_approval_mismatch_rejected():
    g = ApprovalGate(now=lambda: 0.0)
    g.request(_bind())
    assert g.resolve(_bind(params={"v": "9.9.9"}), approve=True) is ApprovalStatus.REJECTED

def test_approval_expiry():
    clock = [0.0]
    g = ApprovalGate(expiry_seconds=120, now=lambda: clock[0])
    g.request(_bind())
    clock[0] = 121.0
    assert g.resolve(_bind(), approve=True) is ApprovalStatus.EXPIRED

# --- audit + idempotency ---
def test_audit_hash_chain_verifies_and_detects_tamper():
    log = AuditLog()
    log.append({"tool": "rollback_deployment", "outcome": "PendingApproval"})
    log.append({"tool": "rollback_deployment", "outcome": "AutoAuthorized"})
    assert log.verify()
    log.entries()[0]["entry"]["outcome"] = "tampered"
    assert not log.verify()

def test_idempotent_at_most_once():
    led = IdempotencyLedger()
    key = ("state1", "cid1")
    first = led.put(key, {"result": "success", "mttr": 42})
    second = led.put(key, {"result": "DIFFERENT"})
    assert first == second  # repeat returns original outcome
