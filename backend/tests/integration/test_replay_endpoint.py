"""Replay endpoint integration: comparison works + original record never mutated (Req 7)."""
import pytest
from fastapi.testclient import TestClient
from app.persistence import Repository
from app.approval import ApprovalGate
from app.api.service import IncidentService
from app.api.app import build_app
from app.contracts import DeciderDecision


class FlipDecider:
    """Selects rollback normally; investigate_further once replay conditions present."""
    def decide(self, state, evidence_snapshot_id, correlation_id=""):
        tool = "investigate_further" if "replay_conditions" in state else "rollback_deployment"
        conf = 0.6 if tool == "investigate_further" else 0.95
        return DeciderDecision(selected=tool, confidence=conf, scores={tool: conf},
                               model_version="fake", latency_ms=100.0, evidence_snapshot_id=evidence_snapshot_id)


@pytest.fixture
def client(tmp_path):
    repo = Repository(url=f"sqlite:///{tmp_path}/t.db")
    svc = IncidentService(repo, FlipDecider(), ApprovalGate(now=lambda: 0.0), bedrock_assess=None)
    return TestClient(build_app(svc)), svc


def test_replay_compares_and_preserves_original(client):
    c, svc = client
    iid = c.post("/api/v1/incidents", json={"scenario_id": "Bad_Deployment", "seed": 42}).json()["incident_id"]
    ev = c.post(f"/api/v1/incidents/{iid}/investigate").json()["evidence_snapshot_id"]
    orig = c.post(f"/api/v1/incidents/{iid}/decide", json={"evidence_snapshot_id": ev}).json()
    assert orig["selected"] == "rollback_deployment"
    orig_decisions_before = len(svc.repo.decisions_for(iid))

    r = c.post(f"/api/v1/incidents/{iid}/replay",
               json={"conditions": {"error_rate_multiplier": 0.05}}).json()
    assert r["replay_incident_id"] != iid
    assert r["tool_changed"] is True
    assert r["labels"]["decider"] == "REAL Decider inference"
    # original incident's decision record is unchanged (immutable)
    assert len(svc.repo.decisions_for(iid)) == orig_decisions_before
    assert svc.repo.decisions_for(iid)[0]["selected_option"] == "rollback_deployment"


def test_replay_invalid_conditions_rejected(client):
    c, _ = client
    iid = c.post("/api/v1/incidents", json={"scenario_id": "Bad_Deployment"}).json()["incident_id"]
    ev = c.post(f"/api/v1/incidents/{iid}/investigate").json()["evidence_snapshot_id"]
    c.post(f"/api/v1/incidents/{iid}/decide", json={"evidence_snapshot_id": ev})
    bad = c.post(f"/api/v1/incidents/{iid}/replay", json={"conditions": {"bogus": 1}})
    assert bad.status_code == 400
