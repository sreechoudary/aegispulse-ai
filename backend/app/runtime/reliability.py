"""
Bedrock reliability: readiness check, bounded warm-up, and bounded retry with
exponential backoff + jitter for TRANSIENT throttling only (Phase 1).

CRITICAL: retries apply ONLY to the read-only Bedrock assessment call. State-changing
remediation is NEVER retried automatically (Req safety; handled by the policy/idempotency
layer, not here).
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

# botocore throttling / transient error codes worth retrying
TRANSIENT_CODES = {"ThrottlingException", "TooManyRequestsException",
                   "ServiceUnavailableException", "ModelTimeoutException",
                   "InternalServerException"}


class BedrockUnavailableError(RuntimeError):
    pass


def _error_code(exc: Exception) -> str:
    resp = getattr(exc, "response", None)
    if isinstance(resp, dict):
        return resp.get("Error", {}).get("Code", "")
    return ""


def with_backoff(fn: Callable[[], T], *, max_attempts: int = 4, base_delay: float = 0.5,
                 max_delay: float = 8.0, sleep: Callable[[float], None] = time.sleep,
                 rng: random.Random | None = None) -> T:
    """Call fn with bounded exponential backoff + full jitter on TRANSIENT errors only.
    Non-transient errors raise immediately. This is for READ-ONLY calls."""
    r = rng or random.Random()
    last: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            code = _error_code(e)
            last = e
            if code not in TRANSIENT_CODES:
                raise
            if attempt == max_attempts - 1:
                break
            delay = min(max_delay, base_delay * (2 ** attempt))
            sleep(r.uniform(0, delay))  # full jitter
    raise BedrockUnavailableError(f"bedrock transient failure after {max_attempts} attempts: {last}")
