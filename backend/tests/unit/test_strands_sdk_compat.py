"""
Strands SDK compatibility regression tests.

Locks in the real-SDK findings from M0 / Wave A so an SDK upgrade that breaks them
fails loudly instead of silently:
  - InterventionHandler requires a `name` property.
  - The intervention actions Proceed/Deny/Confirm/Guide/Transform exist.
  - Agent accepts an `interventions` constructor argument.
  - before_tool_call is declared and returns the typed action union.
"""
import inspect

import pytest

strands = pytest.importorskip("strands")


def test_agent_accepts_interventions_kwarg():
    from strands import Agent
    assert "interventions" in inspect.signature(Agent.__init__).parameters


def test_intervention_actions_exist():
    import strands.interventions as iv
    for name in ("Proceed", "Deny", "Confirm", "Guide", "Transform"):
        assert hasattr(iv, name), f"missing intervention action: {name}"


def test_intervention_handler_requires_name_property():
    from strands import InterventionHandler
    assert "name" in getattr(InterventionHandler, "__abstractmethods__", set())


def test_before_tool_call_declared_with_event_arg():
    from strands import InterventionHandler
    sig = inspect.signature(InterventionHandler.before_tool_call)
    params = list(sig.parameters)
    # self, event, **kwargs  -> typed lifecycle event, not loose args
    assert params[0] == "self"
    assert params[1] == "event"


def test_our_handler_builds_and_has_name():
    from confidence_aware_tool_router import build_intervention_handler
    from strands import InterventionHandler
    h = build_intervention_handler(object(), lambda d: "PendingApproval")
    assert isinstance(h, InterventionHandler)
    assert isinstance(h.name, str) and h.name
