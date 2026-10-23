"""Tests for the backend Decider adapter using a fake package router."""
import pytest
from confidence_aware_tool_router import DeciderDecision as PkgDecision
from confidence_aware_tool_router.core import (
    DeciderUnavailableError as PkgUnavailable,
)
from confidence_aware_tool_router.core import (
    MalformedResponseError as PkgMalformed,
)
from confidence_aware_tool_router.core import (
    OutOfSetError as PkgOutOfSet,
)

from app.contracts import (
    DeciderDecision as ContractDecision,
)
from app.contracts import (
    DeciderUnavailableError,
    MalformedResponseError,
    OutOfSetError,
)
from app.decider import DeciderAdapter


class FakeRouter:
    def __init__(self, result=None, exc=None):
        self._result = result; self._exc = exc
    def decide(self, state, decision, evidence_snapshot_id):
        if self._exc: raise self._exc
        return self._result


def _pkg(tool="rollback_deployment"):
    return PkgDecision(selected=tool, confidence=0.95, scores={tool: 0.95},
                       model="strands-decider-2B-qwen3.5-v1-2610", latency_ms=199.0,
                       evidence_snapshot_id="ev1")


def test_adapter_returns_contract_decision():
    a = DeciderAdapter("http://x", router=FakeRouter(result=_pkg()))
    d = a.decide("state", "ev1", "cid1")
    assert isinstance(d, ContractDecision)
    assert d.selected == "rollback_deployment"
    assert d.model_version.startswith("strands-decider")


def test_adapter_maps_out_of_set():
    a = DeciderAdapter("http://x", router=FakeRouter(exc=PkgOutOfSet("reboot_universe")))
    with pytest.raises(OutOfSetError) as ei:
        a.decide("state", "ev1", "cid1")
    assert ei.value.returned_value == "reboot_universe"
    assert ei.value.correlation_id == "cid1"


def test_adapter_maps_malformed():
    a = DeciderAdapter("http://x", router=FakeRouter(exc=PkgMalformed("bad")))
    with pytest.raises(MalformedResponseError):
        a.decide("state", "ev1")


def test_adapter_maps_unavailable():
    a = DeciderAdapter("http://x", router=FakeRouter(exc=PkgUnavailable("timeout")))
    with pytest.raises(DeciderUnavailableError):
        a.decide("state", "ev1")
