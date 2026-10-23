"""
Append-only, hash-chained audit log + idempotency ledger (Req 6.15, 6.16, 6.17, 12.9).
In-memory for the demo; the persistence layer (WS5) provides the durable store.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _canonical(entry: dict[str, Any]) -> str:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"))


@dataclass
class AuditLog:
    _entries: list[dict[str, Any]] = field(default_factory=list)

    def append(self, entry: dict[str, Any]) -> str:
        prev_hash = self._entries[-1]["entry_hash"] if self._entries else ""
        payload = {"seq": len(self._entries), "prev_hash": prev_hash, "entry": entry}
        entry_hash = hashlib.sha256((prev_hash + _canonical(entry)).encode()).hexdigest()
        payload["entry_hash"] = entry_hash
        self._entries.append(payload)
        return entry_hash

    def verify(self) -> bool:
        prev = ""
        for p in self._entries:
            expect = hashlib.sha256((prev + _canonical(p["entry"])).encode()).hexdigest()
            if expect != p["entry_hash"]:
                return False
            prev = p["entry_hash"]
        return True

    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)


@dataclass
class IdempotencyLedger:
    """At-most-once execution keyed by (incident_state_key, correlation_id)."""
    _done: dict[tuple[str, str], Any] = field(default_factory=dict)
    _attempts: dict[tuple[str, str], int] = field(default_factory=dict)

    def record_attempt(self, key: tuple[str, str]) -> int:
        self._attempts[key] = self._attempts.get(key, 0) + 1
        return self._attempts[key]

    def attempts(self, key: tuple[str, str]) -> int:
        return self._attempts.get(key, 0)

    def get(self, key: tuple[str, str]) -> Any | None:
        return self._done.get(key)

    def put(self, key: tuple[str, str], outcome: Any) -> Any:
        if key not in self._done:
            self._done[key] = outcome
        return self._done[key]
