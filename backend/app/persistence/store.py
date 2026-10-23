"""
Persistence: SQLite via SQLModel with WAL hardening (approved decision).

WAL journal mode + busy_timeout + short write transactions. Repository abstraction
retained so a future Postgres swap touches only this module. Decision_Records and
events are append-only / immutable at the application layer (Req 11, 12.9).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import event
from sqlmodel import Field, Session, SQLModel, create_engine, select


class IncidentRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: str = Field(index=True, unique=True)
    scenario_id: str
    seed: int
    state: str
    correlation_id: str
    created_at: str


class EventRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, unique=True)
    incident_id: str = Field(index=True)
    correlation_id: str
    timestamp: str
    type: str
    payload_json: str


class DecisionRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    decision_record_id: str = Field(index=True, unique=True)
    incident_id: str = Field(index=True)
    record_json: str


def _configure_sqlite(dbapi_conn, _rec):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


class Repository:
    """Data-access boundary. Swap this class to migrate off SQLite."""

    def __init__(self, url: str = "sqlite:///aegispulse.db") -> None:
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", _configure_sqlite)
        SQLModel.metadata.create_all(self.engine)

    # --- incidents ---
    def create_incident(self, **kw) -> None:
        with Session(self.engine) as s:
            s.add(IncidentRow(**kw)); s.commit()

    def set_state(self, incident_id: str, state: str) -> None:
        with Session(self.engine) as s:
            row = s.exec(select(IncidentRow).where(IncidentRow.incident_id == incident_id)).first()
            if row:
                row.state = state; s.add(row); s.commit()

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as s:
            row = s.exec(select(IncidentRow).where(IncidentRow.incident_id == incident_id)).first()
            return row.model_dump() if row else None

    # --- events (append-only) ---
    def append_event(self, envelope: dict[str, Any]) -> None:
        with Session(self.engine) as s:
            s.add(EventRow(event_id=envelope["event_id"], incident_id=envelope["incident_id"],
                           correlation_id=envelope["correlation_id"], timestamp=envelope["timestamp"],
                           type=envelope["type"], payload_json=json.dumps(envelope["payload"])))
            s.commit()

    def events_for(self, incident_id: str, after_event_id: str | None = None) -> list[dict[str, Any]]:
        with Session(self.engine) as s:
            rows = s.exec(select(EventRow).where(EventRow.incident_id == incident_id)
                          .order_by(EventRow.id)).all()
        out = []
        seen = after_event_id is None
        for r in rows:
            if not seen:
                if r.event_id == after_event_id:
                    seen = True
                continue
            out.append({"event_id": r.event_id, "incident_id": r.incident_id,
                        "correlation_id": r.correlation_id, "timestamp": r.timestamp,
                        "type": r.type, "payload": json.loads(r.payload_json)})
        return out

    # --- decision records (immutable) ---
    def save_decision(self, record: dict[str, Any]) -> None:
        with Session(self.engine) as s:
            existing = s.exec(select(DecisionRow).where(
                DecisionRow.decision_record_id == record["decision_record_id"])).first()
            if existing:
                return  # immutable: never overwrite
            s.add(DecisionRow(decision_record_id=record["decision_record_id"],
                              incident_id=record["incident_id"], record_json=json.dumps(record)))
            s.commit()

    def decisions_for(self, incident_id: str) -> list[dict[str, Any]]:
        with Session(self.engine) as s:
            rows = s.exec(select(DecisionRow).where(DecisionRow.incident_id == incident_id)).all()
        return [json.loads(r.record_json) for r in rows]
