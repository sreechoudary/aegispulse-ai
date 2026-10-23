"""
Local entrypoint. Wires the IncidentService with sensible, env-configurable defaults and
exposes a module-level `app` for uvicorn: `uvicorn app.main:app`.

Degrades gracefully: if AWS credentials are absent, Bedrock assessment is skipped (the
Decider still runs). If the Decider server is down, the policy fails closed as designed.
Configuration via environment variables:
  AEGIS_DECIDER_ENDPOINT   default http://127.0.0.1:8777
  AEGIS_DB_URL             default sqlite:///aegispulse.db
  AWS_PROFILE / AWS_REGION  standard AWS resolution (region default us-east-1)
  AEGIS_BEDROCK_MODEL      default amazon.nova-lite-v1:0
  AEGIS_ENABLE_BEDROCK     "1" (default) to enable Bedrock assessment, "0" to disable
"""
from __future__ import annotations
import os

from app.api.app import build_app
from app.api.service import IncidentService
from app.approval import ApprovalGate
from app.decider import DeciderAdapter
from app.persistence import Repository


def _bedrock_assess_or_none():
    if os.getenv("AEGIS_ENABLE_BEDROCK", "1") != "1":
        return None
    try:
        from app.bedrock import BedrockReasoner
        reasoner = BedrockReasoner(
            model_id=os.getenv("AEGIS_BEDROCK_MODEL", "amazon.nova-lite-v1:0"),
            region=os.getenv("AWS_REGION", "us-east-1"),
            profile=os.getenv("AWS_PROFILE") or None,
        )
        return reasoner.assess
    except Exception:  # noqa: BLE001 - Bedrock optional for local dev; degrade gracefully
        return None


def create_app():
    repo = Repository(url=os.getenv("AEGIS_DB_URL", "sqlite:///aegispulse.db"))
    decider = DeciderAdapter(os.getenv("AEGIS_DECIDER_ENDPOINT", "http://127.0.0.1:8777"))
    service = IncidentService(repo, decider, ApprovalGate(), bedrock_assess=_bedrock_assess_or_none())
    return build_app(service)


app = create_app()
