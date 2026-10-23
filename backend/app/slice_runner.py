"""
LIVE vertical-slice runner — REAL Decider + REAL Bedrock through the real IncidentService.
Not a test fixture: this exercises the actual gated path end to end. Prints structured
evidence. Does NOT hard-code the Decider answer; records the actual choice and compares
to the labeled scenario expectation.
"""
from __future__ import annotations

import json
import sys
import tempfile

from app.api.service import IncidentService
from app.approval import ApprovalGate
from app.bedrock import BedrockReasoner
from app.decider import DeciderAdapter
from app.persistence import Repository


def main(decider_endpoint="http://127.0.0.1:8777", scenario="Bad_Deployment", seed=42):
    tmp = tempfile.mkdtemp()
    repo = Repository(url=f"sqlite:///{tmp}/slice.db")
    decider = DeciderAdapter(decider_endpoint)
    reasoner = BedrockReasoner()
    svc = IncidentService(repo, decider, ApprovalGate(now=lambda: 0.0),
                          bedrock_assess=reasoner.assess)

    print("== 1-2. create + simulate ==")
    inc = svc.create(scenario, seed)
    iid = inc["incident_id"]
    print(json.dumps({"incident_id": iid, "health": inc["telemetry"]["service_health"],
                      "summary": inc["telemetry"]["summary"]}, indent=2))

    print("== 3-4. investigate + REAL Bedrock assessment ==")
    invr = svc.investigate(iid)
    ev = invr["evidence_snapshot_id"]
    print("bedrock_model:", reasoner.model_id, "latency_ms:", round(reasoner.last_latency_ms,1),
          "usage:", reasoner.last_usage)
    print("assessment:", invr["assessment"])

    print("== 5-6. REAL Decider selection + policy ==")
    dec = svc.decide(iid, ev)
    print(json.dumps(dec, indent=2))

    actual = dec["selected"]; expected = dec["expected_outcome"]
    print(f"ACTUAL_SELECTION={actual}  EXPECTED_SCENARIO_OUTCOME={expected}  "
          f"MATCH={'yes' if actual==expected else 'no (recorded, not forced)'}")

    print("== 7-8. approval + execute ==")
    if dec["requires_approval"]:
        ap = svc.approve(iid, actual, ev, approve=True)
        print("approval:", ap)
    ex = svc.execute(iid)
    print("recovery:", json.dumps(ex, indent=2))

    print("== 9-10. audit trail + state ==")
    snap = svc.snapshot(iid)
    print("final_state:", snap["incident"]["state"])
    print("decision_records:", len(snap["decisions"]))
    print("audit_chain_valid:", svc.audit.verify())
    print("event_types:", [e["type"] for e in snap["events"]])

    ok = (snap["incident"]["state"] in ("Recovered", "Blocked", "FailedClosed")
          and len(snap["decisions"]) >= 1 and svc.audit.verify())
    print("SLICE_RESULT=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
