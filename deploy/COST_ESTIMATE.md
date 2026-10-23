# AegisPulse AI — Cost Estimate (sandbox compute vs. Bedrock inference)

All figures separate **sandbox compute** from **Bedrock inference**. Vendor unit
prices are marked <TO-CONFIRM> — fill them from the platform's own pricing page
and the current Amazon Bedrock pricing. No dollar rate is fabricated here.

## A. Sandbox compute (8 vCPU / 16 GB)

- Cost model: `sandbox_hourly_rate × hours running`.
- `sandbox_hourly_rate` = <TO-CONFIRM from the Docker Agentic Platform credit
  schedule>. The app runs entirely on this one instance (all 3 containers).
- There is NO additional AWS compute cost: the Decider runs on the sandbox CPU,
  not on EC2 or Bedrock. Expect the instance to be busy during inference (CPU-bound).

## B. Amazon Bedrock inference (only when AEGIS_ENABLE_BEDROCK=1)

Measured token usage (amazon.nova-lite-v1:0):
- ~72 input + ~28 output tokens per incident assessment (~100 tokens total).
- One Bedrock call per incident (the root-cause assessment). The Decider call is free
  (runs locally on the sandbox).

Cost model:
```
bedrock_$ per incident = (72 × input_rate) + (28 × output_rate)
```
where input_rate / output_rate = <TO-CONFIRM per-token Nova Lite pricing>. Nova Lite
is one of the cheapest Bedrock text models, so per-incident Bedrock cost is
fractions of a cent at ~100 tokens; a full demo of a few dozen incidents is negligible.
The 50-case benchmark used ~5.6K input + ~250 output tokens total.

## C. One-time / non-compute

- Model weights download: ~4 GB from Hugging Face, once per volume (free bandwidth;
  may count against sandbox egress — <TO-CONFIRM>).
- No S3, EC2, RDS, or other AWS services are provisioned.

## D. Total (shape)

```
total ≈ (sandbox_hourly_rate × demo_hours) + ($0 AWS compute) + (Bedrock tokens × rate)
```
Dominated by sandbox compute time. Bedrock is negligible at this token volume.
Keep the sandbox stopped when not demoing to conserve credits.

> No cost savings or dollar totals are claimed without the <TO-CONFIRM> rates filled
> in from the authoritative pricing pages.
