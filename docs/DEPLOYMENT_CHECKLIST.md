# AegisPulse AI - AWS Deployment Readiness Checklist

> Status: NOT YET DEPLOYED. Deployment requires EXPLICIT human approval (per project rules).
> This checklist is preparation only; no infrastructure is provisioned.

## Prerequisites
- [ ] Dedicated demo AWS account (NOT the admin SSO role used in dev).
- [ ] Least-privilege IAM instance profile: `bedrock:InvokeModel`/`Converse`, `bedrock:ListFoundationModels`,
      CloudWatch Logs put/create, read-only as needed. **NO** create/delete/update on compute, storage, IAM, DB.
      (Dev used a broad AWSAdministratorAccess SSO role - must be replaced. Req 14.3.)
- [ ] Bedrock model access enabled for `amazon.nova-lite-v1:0` in us-east-1 (confirmed available in dev).

## Instance sizing (UNRESOLVED - measure on target; no fabricated cost)
- [ ] EC2 instance with model-compatible hardware. Observed footprint ~5 GB (MPS, M4 Pro); CPU-only needs
      >=16 GB RAM and shows 7-17x slower Decider latency. GPU g-family gives sub-200ms.
- [ ] Record actual instance type, measured cold-start/warm latency, and hourly cost on that instance.
- [ ] Cost estimate METHOD only: instance_hourly * demo_hours + Bedrock(in_rate*in_tok + out_rate*out_tok).

## Packaging
- [ ] docker-compose: `frontend`, `backend`, `decider` (serve), TLS reverse proxy. (TODO: author compose files.)
- [ ] Decider server warm-up on container start (avoid the ~62s first-call cold spike).
- [ ] Persistent Docker volume for the SQLite DB (WAL enabled).

## Network & secrets
- [ ] Restricted inbound (specific CIDRs); TLS on the public endpoint.
- [ ] Secrets via Secrets Manager / Parameter Store; none committed to git.

## Observability & tags
- [ ] CloudWatch Logs shipping; structured security-event logs.
- [ ] Mandatory tags: Environment, Application, Owner, CostCenter, Compliance, DataClassification, ManagedBy.

## Gate
- [ ] Release gate: >=1 real Decider 2B inference AND >=1 real Bedrock invocation pass (done in dev as G2).
- [ ] Explicit human approval obtained before `terraform apply` / `docker compose up` on AWS.
