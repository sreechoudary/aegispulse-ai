"""FastAPI app exposing the vertical-slice endpoints over the incident service."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.service import IncidentService, StateTransitionError
from app.contracts import ErrorCode
from app.events import sse_format, sse_heartbeat
from app.simulation import InvalidScenarioError, SimulationEngine


class CreateIncidentReq(BaseModel):
    scenario_id: str
    seed: int = 42


class DecideReq(BaseModel):
    evidence_snapshot_id: str


class ApproveReq(BaseModel):
    action: str
    evidence_snapshot_id: str
    decision: str  # "approve" | "reject"


class ReplayReq(BaseModel):
    conditions: dict


def build_app(service: IncidentService) -> FastAPI:
    api = FastAPI(title="AegisPulse AI", version="0.1.0")
    api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])
    sim = SimulationEngine()

    @api.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @api.get("/api/v1/scenarios")
    def scenarios():
        return [{"id": s.scenario_id, "name": s.name, "description": s.description,
                 "expected_outcome": s.expected_outcome} for s in sim.list_scenarios()]

    @api.post("/api/v1/incidents")
    def create(req: CreateIncidentReq):
        try:
            return service.create(req.scenario_id, req.seed)
        except InvalidScenarioError as e:
            raise HTTPException(400, {"code": ErrorCode.VALIDATION_ERROR.value,
                                      "message": str(e), "field": "scenario_id"})

    @api.get("/api/v1/incidents/{incident_id}")
    def get(incident_id: str):
        try:
            return service.snapshot(incident_id)
        except StateTransitionError:
            raise HTTPException(404, {"code": ErrorCode.NOT_FOUND.value, "message": "incident not found"})

    @api.post("/api/v1/incidents/{incident_id}/investigate")
    def investigate(incident_id: str):
        return service.investigate(incident_id)

    @api.post("/api/v1/incidents/{incident_id}/decide")
    def decide(incident_id: str, req: DecideReq):
        try:
            return service.decide(incident_id, req.evidence_snapshot_id)
        except StateTransitionError as e:
            raise HTTPException(409, {"code": ErrorCode.CONFLICT.value, "message": str(e)})

    @api.post("/api/v1/incidents/{incident_id}/approve")
    def approve(incident_id: str, req: ApproveReq):
        return service.approve(incident_id, req.action, req.evidence_snapshot_id,
                               req.decision == "approve")

    @api.post("/api/v1/incidents/{incident_id}/execute")
    def execute(incident_id: str):
        return service.execute(incident_id)

    @api.post("/api/v1/incidents/{incident_id}/replay")
    def replay(incident_id: str, req: ReplayReq):
        from app.replay import InvalidReplayConditionsError
        try:
            return service.replay(incident_id, req.conditions)
        except InvalidReplayConditionsError as e:
            raise HTTPException(400, {"code": ErrorCode.VALIDATION_ERROR.value, "message": str(e)})
        except StateTransitionError as e:
            raise HTTPException(409, {"code": ErrorCode.CONFLICT.value, "message": str(e)})

    @api.get("/api/v1/incidents/{incident_id}/events")
    def events(incident_id: str, last_event_id: str | None = None):
        def gen():
            for ev in service.repo.events_for(incident_id, after_event_id=last_event_id):
                yield sse_format(ev)
            yield sse_heartbeat()
        return StreamingResponse(gen(), media_type="text/event-stream")

    return api
