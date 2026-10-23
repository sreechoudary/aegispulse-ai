# AegisPulse AI — Docker Agentic Platform Deployment Runbook

*Target:** Linux amd64 cloud sandbox, 8 vCPU / 16 GB RAM. Repo:
https://github.com/sreechoudary/aegispulse-ai

> Status: CONFIG PREPARED AND VALIDATED LOCALLY. Not yet deployed. No AWS provisioned.

---

## Architecture (3 containers, one published port)

```
                :8080 (ONLY published port)
  browser → frontend (nginx) —--/api--> backend (FastAPI :8000) —--> decider (:8777, CPU)
                                      └--> Amazon Bedrock (boto3, real inference)
```

- **frontend** (nginx) is the single entry point — serves the built React SPA and
  reverse-proxies `/api` to the backend. SSE buffering is disabled for live events.
- **backend** (FastAPI) — internal only; orchestrates the incident flow.
- **decider** — internal only; runs `strands-decider serve` on CPU.

## Prerequisites on the sandbox

- Docker + Compose v2, linux/amd64.
- Outbound HTTPS to: Hugging Face (model download, ~4 GB, first boot only) and
  Amazon Bedrock (if Bedrock enabled).
- ~15 GB disk (images + model weights).

## Step 1 — clone + build

```
git clone https://github.com/sreechoudary/aegispulse-ai.git
cd aegispulse-ai
docker compose build          # first build pulls torch CPU + deps; allow 10–20 min
```

## Step 2 — supply Bedrock credentials (short-lived, never baked)

Provide temporary least-privilege STS credentials via the platform's secret
mechanism (env or mounted secret) — NOT in the image, NOT in git. Minimum policy:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
  "Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream",
    "bedrock:ListFoundationModels","bedrock:Converse"],
  "Resource":"*"}]}
```

Pass them into the sandbox shell before `compose up` (example; use the platform's
secret injection in practice):

```
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
export AWS_REGION=us-east-1
```

To run WITHOUT Bedrock (Decider only, no AWS): `export AEGIS_ENABLE_BEDROCK=0`.

## Step 3 — launch

```
docker compose up -d
docker compose ps             # wait until all three are healthy
```

Startup order is enforced by healthchecks: decider (model load, ~30–90s on CPU) →
backend → frontend. First boot also downloads the model weights.

Open `http://<sandbox-host>:8080/`.

## Step 4 — validate the Bad Deployment workflow (real Decider)

```
# from inside the sandbox, against the single published port:
curl -s localhost:8080/api/v1/health
IID=$(curl -s -X POST localhost:8080/api/v1/incidents -H 'content-type: application/json' -d '{"scenario_id":"Bad_Deployment","seed":42}' | python3 -c "import sys,json;print(json.load(sys.stdin)['incident_id'])")
EV=$(curl -s -X POST localhost:8080/api/v1/incidents/$IID/investigate | python3 -c "import sys,json;print(json.load(sys.stdin)['evidence_snapshot_id'])")
curl -s -X POST localhost:8080/api/v1/incidents/$IID/decide -H 'content-type: application/json' -d "{\"evidence_snapshot_id\":\"$EV\"}"
```
Expect: `selected=rollback_deployment`, `policy_outcome=PendingApproval` (real
Decider inference). Then `/approve` + `/execute` to see the simulated recovery.

## Health / readiness

- frontend: `GET /healthz` (nginx).
- backend:  `GET /api/v1/health` (200).
- decider:  container healthcheck posts a trivial /v1/systemone call (model loaded).

## Rollback / recovery

```
# roll back to the previous image tag (re-tag before each release):
docker compose down                 # stop all (volumes kept)
git checkout <previous-good-commit>
docker compose up -d --build
# full reset (drop persisted incidents + cached weights):
docker compose down -v
```

Nothing to roll back in AWS: no infrastructure is provisioned, and remediation is
simulation-only — stopping the containers fully reverts the system.

## Security notes

- Only port 8080 is published; decider/backend are internal only.
- No AWS credentials, SSO caches, or tokens are baked into images (`.dockerignore`
  excludes `.aws/`, `.env`, keys, and `docs/validation/`). Creds arrive at runtime only.
- Remediation is simulation-only; the only AWS call is Bedrock `converse` (inference).
- Use short-lived STS credentials; rotate / expire them with the sandbox session.
