"""
AegisPulse AI — FROZEN behavioral contracts (G1).

Protocols the Wave A components must implement. Implementations live in their owning
packages; these signatures are frozen so no component redefines them.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from .enums import ApprovalStatus
from .schemas import (
    ApprovalBinding,
    DeciderDecision,
    PolicyDecision,
    PolicyInput,
)


@runtime_checkable
class ToolRouterProtocol(Protocol):
    """Decider adapter contract (Decider Engineer owns the implementation)."""
    def decide(self, state: str, evidence_snapshot_id: str) -> DeciderDecision:
        """Build the typed choice question, call the real Decider, parse/validate.
        Raises OutOfSetError / MalformedResponseError / DeciderUnavailableError."""
        ...


@runtime_checkable
class PolicyEngineProtocol(Protocol):
    """Deterministic policy contract (SRE Engineer owns the implementation).
    MUST be a pure function of PolicyInput; MUST NOT read Bedrock text (Req 5.6, 6.2)."""
    def authorize(self, inp: PolicyInput) -> PolicyDecision: ...


@runtime_checkable
class ApprovalGateProtocol(Protocol):
    """Approval gate contract (SRE Engineer owns the implementation)."""
    def request(self, binding: ApprovalBinding, expiry_seconds: int) -> str: ...
    def resolve(self, binding: ApprovalBinding, approve: bool) -> ApprovalStatus: ...


@runtime_checkable
class SimulationEngineProtocol(Protocol):
    """Deterministic simulation contract (SRE Engineer owns the implementation)."""
    def generate(self, scenario_id: str, seed: int) -> dict[str, Any]: ...
    def execute(self, tool: str, params: Mapping[str, Any]) -> dict[str, Any]: ...


# Frozen typed exceptions for the Decider adapter (shared so policy can map to fail-closed).
class OutOfSetError(ValueError):
    def __init__(self, returned_value: str, correlation_id: str) -> None:
        self.returned_value = returned_value
        self.correlation_id = correlation_id
        super().__init__(f"Decider returned out-of-set tool {returned_value!r}")


class MalformedResponseError(ValueError):
    pass


class DeciderUnavailableError(RuntimeError):
    pass
