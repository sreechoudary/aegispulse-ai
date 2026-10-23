"""
Confidence-Aware Recovery Tool Router — reusable #tool-selection pattern.

Standalone, independently importable. Depends ONLY on the Python stdlib (urllib) and
the Strands Agents SDK for the optional intervention helper. No AegisPulse app imports.

Wraps the real Strands Decider `POST /v1/systemone` serve contract: it asks one typed
`choice` question over a fixed option set and returns the selected option with a
calibrated confidence and per-option scores.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import urllib.request
import urllib.error

# Default fixed option set for the recovery-tool decision. Single source of truth
# within the package: used BOTH to build the request criteria keys and to validate
# the returned choice.
DEFAULT_RECOVERY_TOOLS: tuple[str, ...] = (
    "rollback_deployment",
    "scale_out_service",
    "restart_unhealthy_tasks",
    "investigate_further",
    "escalate_to_human",
)


class OutOfSetError(ValueError):
    """Decider returned a choice outside the declared option set."""
    def __init__(self, returned_value: str) -> None:
        self.returned_value = returned_value
        super().__init__(f"Decider returned out-of-set choice {returned_value!r}")


class MalformedResponseError(ValueError):
    """Decider response was missing a required field or had an invalid value."""


class DeciderUnavailableError(RuntimeError):
    """Decider did not respond within the timeout or the connection failed."""


@dataclass(frozen=True)
class ToolChoiceDecision:
    """Typed definition of a one-of-N recovery-tool choice."""
    question_id: str
    options: tuple[str, ...]
    prompt: str
    criteria: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.options:
            raise ValueError("options must be non-empty")
        if self.criteria:
            unknown = set(self.criteria) - set(self.options)
            if unknown:
                raise ValueError(f"criteria keys not in options: {sorted(unknown)}")


@dataclass(frozen=True)
class DeciderDecision:
    """Normalized decision. Maps FROM the serve response:
    selected<-answers[qid].choice, scores<-probabilities, confidence<-confidence,
    model<-model, latency_ms<-latency_ms."""
    selected: str
    confidence: float
    scores: dict[str, float]
    model: str
    latency_ms: float
    evidence_snapshot_id: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence {self.confidence} out of [0,1]")


class _Transport:
    """Minimal injectable HTTP transport so tests can fake the Decider."""
    def post_json(self, url: str, body: dict, timeout_s: float) -> dict:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"content-type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            raise DeciderUnavailableError(str(e)) from e
        except TimeoutError as e:
            raise DeciderUnavailableError(f"timeout after {timeout_s}s") from e


class ConfidenceAwareToolRouter:
    """Calls the real Decider serve endpoint and returns a validated DeciderDecision."""

    def __init__(self, endpoint: str, timeout_s: float = 10.0, transport: _Transport | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s
        self._transport = transport or _Transport()

    def build_request(self, state: str, decision: ToolChoiceDecision) -> dict:
        criteria = decision.criteria or {opt: opt for opt in decision.options}
        return {
            "state": state,
            "questions": {
                decision.question_id: {
                    "type": "choice",
                    "instructions": decision.prompt,
                    "criteria": criteria,
                }
            },
        }

    def decide(self, state: str, decision: ToolChoiceDecision, evidence_snapshot_id: str) -> DeciderDecision:
        body = self.build_request(state, decision)
        url = f"{self.endpoint}/v1/systemone"
        raw = self._transport.post_json(url, body, self.timeout_s)
        try:
            answers = raw["answers"]
            ans = answers[decision.question_id]
            choice = ans["choice"]
            probabilities = ans["probabilities"]
            confidence = ans["confidence"]
            model = raw["model"]
            latency_ms = raw["latency_ms"]
        except (KeyError, TypeError) as e:
            raise MalformedResponseError(f"missing required field: {e}") from e

        if choice not in decision.options:
            raise OutOfSetError(choice)
        if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            raise MalformedResponseError(f"confidence {confidence!r} invalid")

        return DeciderDecision(
            selected=choice,
            confidence=float(confidence),
            scores={k: float(v) for k, v in probabilities.items()},
            model=str(model),
            latency_ms=float(latency_ms),
            evidence_snapshot_id=evidence_snapshot_id,
        )
