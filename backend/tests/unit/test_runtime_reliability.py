"""Phase 1 runtime reliability tests (no network — fakes + injected clock/rng)."""
import pytest
from app.runtime.reliability import with_backoff, BedrockUnavailableError, TRANSIENT_CODES
from app.runtime import LatencyLog


class FakeClientError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}


def test_backoff_succeeds_first_try():
    calls = []
    assert with_backoff(lambda: calls.append(1) or "ok", sleep=lambda s: None) == "ok"
    assert len(calls) == 1


def test_backoff_retries_transient_then_succeeds():
    n = {"i": 0}
    def fn():
        n["i"] += 1
        if n["i"] < 3:
            raise FakeClientError("ThrottlingException")
        return "ok"
    out = with_backoff(fn, max_attempts=5, sleep=lambda s: None)
    assert out == "ok" and n["i"] == 3


def test_backoff_does_not_retry_non_transient():
    n = {"i": 0}
    def fn():
        n["i"] += 1
        raise FakeClientError("AccessDeniedException")
    with pytest.raises(FakeClientError):
        with_backoff(fn, max_attempts=5, sleep=lambda s: None)
    assert n["i"] == 1  # no retry on non-transient


def test_backoff_exhausts_and_raises_unavailable():
    def fn():
        raise FakeClientError("ThrottlingException")
    with pytest.raises(BedrockUnavailableError):
        with_backoff(fn, max_attempts=3, sleep=lambda s: None)


def test_latency_log_percentiles_separate_cold_from_warm():
    log = LatencyLog()
    log.cold_start_ms = 62000.0
    log.warm_samples_ms = [500.0, 600.0, 700.0, 800.0, 900.0]
    assert log.cold_start_ms == 62000.0
    assert log.p(50) == 700.0
    assert log.p(95) == 900.0
    # cold is NOT mixed into warm percentiles
    assert log.cold_start_ms not in log.warm_samples_ms
