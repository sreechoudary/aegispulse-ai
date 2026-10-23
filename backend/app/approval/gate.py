"""
Approval Gate (Req 6.9-6.13, 12.8).

Binds each approval to the exact (incident_id, action, action_parameters,
evidence_snapshot_id) tuple. Rejects on any field mismatch or after expiry. Time is
injectable so tests are deterministic (no real clock dependence).
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from app.contracts import (
    DEFAULT_APPROVAL_EXPIRY_SECONDS,
    ApprovalBinding,
    ApprovalStatus,
)


def _key(b: ApprovalBinding) -> str:
    return json.dumps({
        "incident_id": b.incident_id, "action": b.action,
        "action_parameters": b.action_parameters, "evidence_snapshot_id": b.evidence_snapshot_id,
    }, sort_keys=True)


@dataclass
class _Pending:
    binding_key: str
    created_at: float
    expires_at: float
    status: ApprovalStatus


class ApprovalGate:
    def __init__(self, expiry_seconds: int = DEFAULT_APPROVAL_EXPIRY_SECONDS,
                 now: Callable[[], float] | None = None) -> None:
        self.expiry_seconds = expiry_seconds
        self._now = now or time.monotonic
        self._pending: dict[str, _Pending] = {}

    def request(self, binding: ApprovalBinding) -> str:
        key = _key(binding)
        t = self._now()
        self._pending[key] = _Pending(key, t, t + self.expiry_seconds, ApprovalStatus.REQUESTED)
        return key

    def resolve(self, binding: ApprovalBinding, approve: bool) -> ApprovalStatus:
        key = _key(binding)
        p = self._pending.get(key)
        if p is None:
            # exact-match binding failed (mismatch or never requested)
            return ApprovalStatus.REJECTED
        if self._now() > p.expires_at:
            p.status = ApprovalStatus.EXPIRED
            return ApprovalStatus.EXPIRED
        p.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        return p.status

    def status(self, binding: ApprovalBinding) -> ApprovalStatus:
        p = self._pending.get(_key(binding))
        if p is None:
            return ApprovalStatus.NONE
        if p.status is ApprovalStatus.REQUESTED and self._now() > p.expires_at:
            p.status = ApprovalStatus.EXPIRED
        return p.status
