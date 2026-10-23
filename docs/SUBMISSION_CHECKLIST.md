# AegisPulse AI — Submission Checklist (updated 2026-10-18)

Verified against the official hackathon requirements (AWS Builder Center — Agent Experience
Hackathon: Strands Decider). **Projects due October 23.** Prize: $5,000 AWS credits x3.

## Official qualification requirements
| Requirement | Status | Evidence |
|-------------|--------|----------|
| Agent uses Decider 2B for >=1 meaningful decision, paired with Bedrock | DONE | Live G2 + journey: Bedrock assess -> Decider select -> policy -> approval -> recovery |
| Builder Center article (agent, what it does, the decision handed to Decider) | DRAFT READY | docs/BUILDER_CENTER_ARTICLE.md (publish = human action) |
| Public repo with source + >=1 reusable Decider decision pattern | READY (unpublished) | patterns/confidence_aware_tool_router/ ; publish = human action |
| Public demo video < 3 min | SCRIPT+STORYBOARD READY | docs/DEMO_SCRIPT.md, docs/VIDEO_STORYBOARD.md (record = human action) |
| Declare one decision pattern | DONE | #tool-selection |
| Original agent, not previously published | ASSERTED | net-new project |
| Tags: #strands-decider-2b + one pattern tag | DONE | #strands-decider-2b #tool-selection in README, article, package |

## Judging rubric readiness (Creativity 30 / Decider use 30 / Communication 25 / Originality 15)
- Creativity: incident-commander arena, Time Machine replay, mission-control dashboard.
- Decider use: real Decider 2B drives tool selection; reusable pattern; measured latency bonus.
- Communication: article + storyboard + honest benchmark with limitations.
- Originality: confidence-gated deterministic-policy incident commander.

## Engineering acceptance
- [x] App starts from documented commands (README).
- [x] Five scenarios, distinct deterministic telemetry.
- [x] Real Decider 2B + real Bedrock demonstrated (G2).
- [x] Decider controls tool selection; policy gates enforced (0% unsafe all arms).
- [x] Simulated recovery completes; counterfactual replay works (honest when unchanged).
- [x] Benchmark reproducible; original preserved; equal-context results documented.
- [x] Reusable pattern imports independently.
- [x] Tests pass (backend 81, frontend 2); ruff + mypy clean on core.
- [x] No secrets committed (security review: 0 findings).
- [x] Demo completable < 3 min (script + fallbacks).

## Deliverable artifacts produced
- README.md, LICENSE (Apache-2.0 header + paste-in note), NOTICE.md
- docs/BUILDER_CENTER_ARTICLE.md, docs/DEMO_SCRIPT.md, docs/VIDEO_STORYBOARD.md
- docs/DEPLOYMENT_CHECKLIST.md, docs/SECURITY_REVIEW.md, docs/contracts/G1_CONTRACTS.md
- evaluation/ (original preserved, final live, dev/eval cases, BENCHMARK_REPORT.md)
- .gitignore

## ACTIONS REQUIRING YOUR APPROVAL / HUMAN ACTION (none done automatically)
1. Paste full Apache-2.0 license text into LICENSE.
2. Final human license review of NOTICE.md.
3. `git init`, verify against .gitignore, create the repo, and **publish** it (your approval).
4. **Record** the <3-min demo video with warm models (your action) and fill VIDEO_URL_PLACEHOLDER.
5. **Publish** the Builder Center article (your approval) and fill REPO_URL_PLACEHOLDER.
6. Export an architecture.png from the design.md Mermaid diagram for the article.
7. **Submit** the hackathon entry with both tags before Oct 23 (your approval).
8. (Optional, separate approval) AWS deployment — checklist in docs/DEPLOYMENT_CHECKLIST.md; NOT done.

## Explicitly NOT done (per instructions)
- No AWS infrastructure provisioned.
- Repository NOT published.
- Builder Center article NOT published.
- Hackathon entry NOT submitted.
