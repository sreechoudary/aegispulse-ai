# Confidence-Aware Recovery Tool Router

A small, reusable **`#tool-selection`** decision pattern built on the real
**`#strands-decider-2b`** model. It asks the Strands Decider one typed `choice`
question over a fixed option set and returns the selected option with a calibrated
confidence and per-option scores — so ordinary deterministic code (not an LLM) makes
the final policy decision.

Tags: `#strands-decider-2b` `#tool-selection`

## Why

Decision models like Strands Decider 2B pick from options and return a calibrated
confidence. This package wraps the Decider `POST /v1/systemone` serve contract behind
a typed API so an agent can route to the next recovery tool quickly, cheaply, and with
a confidence you can gate on — while a separate policy layer decides what to *do*.

## Install

```
pip install -e .            # standalone, stdlib only
pip install -e ".[strands]" # add the Strands intervention helper
```

The package is independently importable and depends on **no application code**.

## Usage

```python
from confidence_aware_tool_router import (
    ConfidenceAwareToolRouter, ToolChoiceDecision, DEFAULT_RECOVERY_TOOLS,
)

router = ConfidenceAwareToolRouter("http://127.0.0.1:8000", timeout_s=10.0)
decision = ToolChoiceDecision(
    question_id="recovery_tool",
    options=DEFAULT_RECOVERY_TOOLS,
    prompt="Select the single best recovery tool for this incident.",
    criteria={t: t.replace("_", " ") for t in DEFAULT_RECOVERY_TOOLS},
)
result = router.decide(state="...incident summary...", decision=decision,
                       evidence_snapshot_id="ev-123")
print(result.selected, result.confidence, result.scores)
```

### Optional Strands intervention

```python
from confidence_aware_tool_router import build_intervention_handler, map_to_action
# policy(decision) -> "AutoAuthorized" | "PendingApproval" | "Blocked" | "FailedClosed"
handler = build_intervention_handler(router, policy)
# agent = Agent(interventions=[handler])
```

`map_to_action(decision, policy_outcome)` is a pure function (easy to unit-test):
high-blast-radius or PendingApproval -> `Confirm`; Blocked/FailedClosed -> `Deny`;
`investigate_further` -> `Guide`; AutoAuthorized -> `Proceed`.

## Safety guidance

- The Decider **selects**; it does not authorize. Always gate the selection through a
  deterministic policy you control, and require human approval for high-blast-radius
  actions regardless of confidence.
- Treat any text you feed into `state` as untrusted; never let model output trigger a
  state-changing action without passing your policy gate.
- On any Decider failure (out-of-set choice, malformed response, timeout) the router
  raises a typed exception — **fail closed** for state-changing actions.

## Limitations

- Choice-only (`type: "choice"`); it does not wrap the Decider `noul`/`score` types.
- Validated against `strands-decider` 0.1.0 and `strands-agents` 1.61.1.
  **SDK delta:** `strands.InterventionHandler` requires a `name` property, and
  `before_tool_call` receives a typed lifecycle event (not loose args). This package
  implements `name` and reads the decision off the event; adjust if the SDK changes.
- The reusable `build_intervention_handler` reads the decision from an
  `event.aegis_decision` attribute by convention — wire that in your agent, or call
  `map_to_action` directly.

## Tests

```
pytest
```
