"""
Bedrock reasoner (real inference). Reasoning/explanation ONLY — never selects a tool
or alters policy (Req 5.5, 5.6). Treats output as untrusted (length-capped).

Phase 1 reliability: region/model readiness check, optional bounded warm-up, and
bounded backoff+jitter on transient throttling for the READ-ONLY assess() call.
Cold-start and warm latencies are tracked separately.
"""
from __future__ import annotations

import time

import boto3

from app.runtime.reliability import with_backoff


class BedrockReasoner:
    def __init__(self, model_id: str = "amazon.nova-lite-v1:0", region: str = "us-east-1",
                 profile: str | None = "ar-dev", max_attempts: int = 4) -> None:
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.client = session.client("bedrock-runtime", region_name=region)
        self._ctl = session.client("bedrock", region_name=region)
        self.model_id = model_id
        self.region = region
        self.max_attempts = max_attempts
        self.cold_latency_ms: float | None = None
        self.warm_latencies_ms: list[float] = []
        self.last_latency_ms = 0.0
        self.last_usage: dict = {}
        self._warmed = False

    def ready(self) -> bool:
        """Readiness: configured model id is available in the configured region."""
        try:
            models = self._ctl.list_foundation_models().get("modelSummaries", [])
            return any(self.model_id in m.get("modelId", "") for m in models)
        except Exception:  # noqa: BLE001 - readiness probe must never raise
            return False

    def warm_up(self) -> float:
        """Bounded warm-up: one tiny real call to absorb cold start. Returns latency ms."""
        t0 = time.time()
        self._invoke("warm up: respond OK")
        dt = (time.time() - t0) * 1000
        self.cold_latency_ms = dt
        self._warmed = True
        return dt

    def assess(self, summary: str) -> str:
        t0 = time.time()
        text = self._invoke(
            "In one sentence, assess the most likely root cause of this incident: " + summary)
        dt = (time.time() - t0) * 1000
        self.last_latency_ms = dt
        if self._warmed:
            self.warm_latencies_ms.append(dt)
        return text[:500]  # untrusted output, length-capped

    def _invoke(self, prompt: str) -> str:
        def call() -> str:
            r = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 100, "temperature": 0.2})
            self.last_usage = r.get("usage", {})
            return r["output"]["message"]["content"][0]["text"].strip()
        return with_backoff(call, max_attempts=self.max_attempts)

    def latency_p(self, pct: float) -> float | None:
        if not self.warm_latencies_ms:
            return None
        s = sorted(self.warm_latencies_ms)
        i = min(len(s) - 1, round((pct / 100.0) * (len(s) - 1)))
        return s[i]
