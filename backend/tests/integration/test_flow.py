"""End-to-end backend flow test using a FAKE Decider (no real inference needed here)."""
import pytest
from fastapi.testclient import TestClient

from app.api.app import build_app
from app.api.service import IncidentService
from app.approval import ApprovalGate
from app.contracts import DeciderDecision
from app.persistence import Repository


class FakeDecider:
    def __init__(self, tool="rollback_deployment", conf=0.95):
        self.tool = tool; self.conf = conf
    def decide(self, state, evidence_snapshot_id, correlation_id=""):
        return DeciderDecision(selected=self.tool, confidence=self.conf,
                               scores={self.tool: self.conf}, model_version="fake-decider",
                               latency_ms=120.0, evidence_snapshot_id=evidence_snapshot_id)


@pytest.fixture
def client(tmp_path):
    repo = Repository(url=f"sqlite:///{tmp_path}/t.db")
    svc = IncidentService(repo, FakeDecider(), ApprovalGate(now=lambda: 0.0),
                          bedrock_assess=lambda s: "assessment: likely bad deploy")
    return TestClient(build_app(svc))


def test_full_bad_deployment_flow(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    assert len(client.get("/api/v1/scenarios").json()) == 5

    r = client.post("/api/v1/incidents", json={"scenario_id": "Bad_Deployment", "seed": 42}).json()
    iid = r["incident_id"]

    inv = client.post(f"/api/v1/incidents/{iid}/investigate").json()
    ev = inv["evidence_snapshot_id"]
    assert inv["assessment"]

    dec = client.post(f"/api/v1/incidents/{iid}/decide", json={"evidence_snapshot_id": ev}).json()
    assert dec["selected"] == "rollback_deployment"
    assert dec["policy_outcome"] == "PendingApproval"  # high-blast always needs approval
    assert dec["expected_outcome"] == "rollback_deployment"  # matches labeled scenario expectation

    ap = client.post(f"/api/v1/incidents/{iid}/approve",
                     json={"action": "rollback_deployment", "evidence_snapshot_id": ev,
                           "decision": "approve"}).json()
    assert ap["approval_status"] == "approved"

    ex = client.post(f"/api/v1/incidents/{iid}/execute").json()
    assert ex["recovery"]["result"] == "success"

    snap = client.get(f"/api/v1/incidents/{iid}").json()
    assert snap["incident"]["state"] == "Recovered"
    assert len(snap["decisions"]) >= 1
    types = [e["type"] for e in snap["events"]]
    for t in ["telemetry_generated", "decider_decision", "policy_evaluated",
              "approval_granted", "action_executed", "recovery_measured"]:
        assert t in types


def test_invalid_scenario_rejected(client):
    r = client.post("/api/v1/incidents", json={"scenario_id": "Nope", "seed": 1})
    assert r.status_code == 400


def test_sse_events_stream(client):
    iid = client.post("/api/v1/incidents", json={"scenario_id": "Bad_Deployment"}).json()["incident_id"]
    client.post(f"/api/v1/incidents/{iid}/investigate")
    body = client.get(f"/api/v1/incidents/{iid}/events").text
    assert "event: telemetry_generated" in body
    assert "id: evt_" in body
