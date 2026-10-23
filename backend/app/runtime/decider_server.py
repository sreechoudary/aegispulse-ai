"""
Decider model-server lifecycle management (Phase 1 runtime reliability).

Starts `strands-decider serve` once, polls readiness, monitors health, and shuts down
gracefully. The model loads once and is reused across requests (the server process
holds it in memory). Separates cold-start from warm-inference latency measurement.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class LatencyLog:
    cold_start_ms: float | None = None
    warm_samples_ms: list[float] = field(default_factory=list)

    def p(self, pct: float) -> float | None:
        if not self.warm_samples_ms:
            return None
        s = sorted(self.warm_samples_ms)
        i = min(len(s) - 1, round((pct / 100.0) * (len(s) - 1)))
        return s[i]


class DeciderServer:
    """Manages a single strands-decider serve process."""

    def __init__(self, model: str, port: int = 8777, device: str = "mps",
                 python_bin: str = ".venv-validation/bin/strands-decider") -> None:
        self.model = model
        self.port = port
        self.device = device
        self.python_bin = python_bin
        self.base = f"http://127.0.0.1:{port}"
        self._proc: subprocess.Popen | None = None
        self.latency = LatencyLog()

    def start(self, ready_timeout_s: float = 120.0) -> float:
        """Start the server and block until ready. Returns startup-to-ready seconds."""
        if self.is_listening():
            return 0.0
        t0 = time.time()
        self._proc = subprocess.Popen(
            [self.python_bin, "serve", self.model, "--device", self.device,
             "--port", str(self.port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = t0 + ready_timeout_s
        while time.time() < deadline:
            if self.is_listening() and self.health():
                dt = time.time() - t0
                self.latency.cold_start_ms = dt * 1000
                return dt
            time.sleep(1.0)
        raise TimeoutError(f"Decider server not ready within {ready_timeout_s}s")

    def is_listening(self) -> bool:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", self.port)) == 0

    def health(self) -> bool:
        """Readiness probe: a trivial systemone call must return a parseable answer."""
        try:
            body = json.dumps({"state": "ping", "questions": {
                "q": {"type": "noul", "instructions": "Is this a readiness probe?"}}}).encode()
            req = urllib.request.Request(f"{self.base}/v1/systemone", data=body,
                                         headers={"content-type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                return "answers" in json.loads(r.read())
        except Exception:  # noqa: BLE001 - readiness probe must never raise
            return False

    def shutdown(self, grace_s: float = 5.0) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None
