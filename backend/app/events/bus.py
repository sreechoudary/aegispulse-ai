"""
Event helpers + ULID-ish monotonic ids for SSE (approved: ids, heartbeat, Last-Event-ID
durable replay). Events are persisted before fan-out so replay is durable (Req 10.5, 11.3).
"""
from __future__ import annotations

import itertools
import time
from datetime import UTC, datetime
from typing import Any

from app.contracts import EventType

_counter = itertools.count(1)


def new_event_id() -> str:
    # monotonic, sortable: time-based prefix + counter
    return f"evt_{int(time.time()*1000):013d}_{next(_counter):06d}"


def iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.") +         f"{datetime.now(UTC).microsecond // 1000:03d}Z"


def make_event(incident_id: str, correlation_id: str, etype: EventType,
               payload: dict[str, Any]) -> dict[str, Any]:
    return {"event_id": new_event_id(), "incident_id": incident_id,
            "correlation_id": correlation_id, "timestamp": iso_now(),
            "type": etype.value, "payload": payload}


def sse_format(envelope: dict[str, Any]) -> str:
    import json
    return f"id: {envelope['event_id']}\nevent: {envelope['type']}\ndata: {json.dumps(envelope)}\n\n"


def sse_heartbeat() -> str:
    return ": heartbeat\n\n"
