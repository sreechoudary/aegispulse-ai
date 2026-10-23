# Requirements Document

## Introduction

AegisPulse AI — Detect. Decide. Defend. — is an interactive cloud incident-response arena built for the October 2026 AWS Strands Decider 2B Agent Experience Hackathon (submission deadline October 23, 2026). Users launch realistic synthetic production incidents, watch a Strands agent investigate telemetry, observe the Strands Decider 2B model select a recovery tool with calibrated confidence, review deterministic safety-policy decisions, approve safe simulated recovery actions, and compare counterfactual incident outcomes on replay.

The central goal is to demonstrate clearly what the Strands Decider 2B model contributes beyond a Bedrock-only agent: calibrated, confidence-aware tool selection that materially drives the recovery workflow, gated by a separate deterministic safety policy. The Decider selects the candidate recovery tool, a separate deterministic policy engine authorizes or blocks execution, and Amazon Bedrock provides reasoning and explanations without overriding either decision. All remediation is simulation-only; the system never touches real production resources.

This requirements document frames non-functional requirements around the hackathon judging criteria — Creativity/cool factor (30%), Effective use of Strands Decider 2B (30%), Communication quality (25%), and Originality (15%) — plus the under-3-minute demo constraint and the confidence-calibration safety threshold.

## Glossary

- **AegisPulse**: The overall product and system under specification.
- **Incident_Arena**: The primary dashboard screen where users launch and observe incidents.
- **Simulation_Engine**: The deterministic component that generates synthetic telemetry and executes permitted remediation actions against a simulated environment only.
- **Strands_Agent**: The Strands Agents SDK orchestration layer that gathers evidence via tools and coordinates the incident workflow.
- **Decider**: The real Strands Decider 2B model accessed through the documented `strands-decider` package and `POST /v1/systemone` HTTP contract.
- **Tool_Router**: The "Confidence-Aware Recovery Tool Router" pattern that submits a typed `choice` question with a fixed tool option set to the Decider and returns the selected recovery tool with calibrated confidence.
- **Recovery_Tool**: One member of the fixed option set — `rollback_deployment`, `scale_out_service`, `restart_unhealthy_tasks`, `investigate_further`, or `escalate_to_human`.
- **Bedrock_Reasoner**: The Amazon Bedrock integration used for evidence interpretation, hypothesis generation, human-readable explanations, and post-incident summaries.
- **Safety_Policy**: The separate deterministic policy engine that authorizes or blocks the Decider-recommended action based on allowlisting, evidence, confidence, blast radius, and approval rules, independently of the Decider selection and the Bedrock_Reasoner.
- **Approval_Gate**: The mechanism requiring explicit human approval before a high-impact simulated action executes.
- **Confidence_Threshold**: The calibration guidance value with a default of 0.90 that is configurable. The threshold gates only automatic state-changing actions; answers at or above the threshold are reliable on short classification tasks, and answers below the threshold block automatic state-changing remediation while still permitting read-only investigation, additional evidence collection, and escalation.
- **Incident_Time_Machine**: The counterfactual replay feature allowing users to re-run an incident with modified conditions.
- **Benchmark_Harness**: The component that compares Bedrock-only tool selection against Decider 2B tool selection over synthetic evaluation cases.
- **Evidence_Snapshot**: An immutable, identified capture of the incident state and evidence references submitted to the Decider for a decision.
- **Decision_Record**: An immutable record that captures the complete context and outcome of a single Decider-driven decision, including input state, evidence references, typed question, available options, selected option, confidence, model version identifier, inference latency, policy outcome, approval status, and execution result.
- **Correlation_ID**: A unique identifier attached to each request and propagated through logs and events for traceability.
- **System_One_Request**: A request to the Decider HTTP endpoint `POST /v1/systemone` with a `state` and `questions` payload.

## Requirements

### Requirement 1: Deterministic Incident Simulation Engine

**User Story:** As a hackathon demo viewer, I want realistic synthetic production incidents generated deterministically, so that I can observe reproducible incident-response behavior.

#### Acceptance Criteria

1. THE Simulation_Engine SHALL provide exactly five predefined incident scenarios identified as Bad_Deployment, Capacity_Saturation, Memory_Leak, Database_Connection_Exhaustion, and Ambiguous_Incident.
2. WHEN a user selects one of the five predefined scenarios, THE Simulation_Engine SHALL generate synthetic telemetry for that scenario that includes service health indicators, request metrics, and error metrics, where each telemetry series contains at least one data point and every metric value is non-negative.
3. WHERE a fixed integer random seed in the range 0 to 4,294,967,295 is provided, THE Simulation_Engine SHALL produce byte-for-byte identical telemetry across repeated runs of the same scenario with the same seed.
4. THE Simulation_Engine SHALL execute remediation actions only against the simulated environment and SHALL NOT issue any create, update, or delete operation against a real cloud resource.
5. WHEN the Simulation_Engine executes a permitted Recovery_Tool, THE Simulation_Engine SHALL return a recovery outcome containing a simulated mean-time-to-recovery value expressed in seconds, a service impact indicator, and an action result of either success or failure.
6. IF a requested scenario identifier is not exactly one of the five predefined scenario identifiers, THEN THE Simulation_Engine SHALL reject the request, return a structured error that names the invalid scenario identifier, and generate no telemetry.
7. THE Simulation_Engine SHALL expose, for each of the five scenarios, a labeled expected recovery outcome that is used as the test expectation and is sourced independently of any Decider response.
8. THE Simulation_Engine SHALL execute all remediation exclusively against simulated infrastructure and SHALL hold no permission capable of mutating a production AWS resource.

### Requirement 2: Strands Agent Orchestration

**User Story:** As a demo viewer, I want a Strands agent to investigate the incident and coordinate the workflow, so that I can see autonomous evidence gathering before any recovery decision.

#### Acceptance Criteria

1. THE Strands_Agent SHALL use the Strands Agents SDK to orchestrate the incident-response workflow.
2. WHEN an incident investigation begins, THE Strands_Agent SHALL gather evidence by invoking each registered telemetry-reading tool against the Simulation_Engine exactly once before producing an Evidence_Snapshot.
3. THE Strands_Agent SHALL record each tool invocation as an agent-execution-timeline event with an ISO-8601 millisecond-precision timestamp and a Correlation_ID.
4. THE Strands_Agent SHALL integrate the Decider recommendation through the documented InterventionHandler mechanism with a `before_tool_call` method passed via the agent's `interventions` configuration.
5. WHEN the InterventionHandler `before_tool_call` returns a Confirm action, THE Strands_Agent SHALL enter a pending-approval state and preserve that state until a human decision is recorded before proceeding.
6. WHEN the InterventionHandler `before_tool_call` returns a Deny action, THE Strands_Agent SHALL NOT execute the proposed tool call and SHALL record a denied-action timeline event with the Correlation_ID.
7. IF a tool invocation raises an error, THEN THE Strands_Agent SHALL record the error as a timeline event including the Correlation_ID, retain the gathered evidence, and continue the workflow without executing an unverified action.

### Requirement 3: Confidence-Aware Recovery Tool Router (Decider 2B Integration)

**User Story:** As a judge evaluating Decider 2B usage, I want the Strands Decider 2B model to select the recovery tool with calibrated confidence, so that I can see the model materially driving the recovery workflow.

#### Acceptance Criteria

1. THE Tool_Router SHALL submit a typed `choice` question to the Decider with the fixed option set `rollback_deployment`, `scale_out_service`, `restart_unhealthy_tasks`, `investigate_further`, and `escalate_to_human`.
2. THE Tool_Router SHALL call the real Strands Decider 2B model via the documented `strands-decider` package and the `POST /v1/systemone` endpoint with a body containing `state` and `questions`.
3. WHEN the Decider returns a response, THE Tool_Router SHALL parse the selected Recovery_Tool, the calibrated confidence bounded to the range 0.0 to 1.0, per-option scores where supported, the decision latency expressed in milliseconds, the model identifier, and the Evidence_Snapshot identifier.
4. THE Tool_Router SHALL select the candidate recovery action from the Recovery_Tool returned by the Decider, and THE Safety_Policy SHALL separately authorize or block that candidate before execution.
5. THE Bedrock_Reasoner SHALL NOT override or bypass the Recovery_Tool selected by the Decider.
6. THE Tool_Router SHALL include the input incident state, evidence references, the explicit typed question, and the fixed tool option set in each System_One_Request.
7. THE Tool_Router SHALL record every decision as a Decision_Record and SHALL forward the Decision_Record for persistence as defined in Requirement 11.
8. IF the Decider returns a tool outside the fixed option set, THEN THE Tool_Router SHALL reject the response, record a structured validation error that includes the returned out-of-set value and the Correlation_ID, and THE Safety_Policy SHALL fail closed by blocking all state-changing actions while permitting read-only investigation and human escalation.
9. IF a required field is missing from the Decider response or the response is malformed, THEN THE Tool_Router SHALL record a structured validation error and THE Safety_Policy SHALL fail closed by blocking all state-changing actions while permitting read-only investigation and human escalation.
10. IF the Decider service is unavailable or does not respond within a 10-second request timeout, THEN THE Tool_Router SHALL treat the service as unavailable, return a structured error, and THE Safety_Policy SHALL fail closed by blocking all state-changing actions while permitting read-only investigation and human escalation.

### Requirement 4: Reusable Confidence-Aware Tool Router Package

**User Story:** As an open-source contributor, I want the tool-selection pattern packaged as a reusable, independently importable module, so that I can adopt the pattern in other Strands projects.

#### Acceptance Criteria

1. THE Tool_Router SHALL be packaged under `patterns/confidence_aware_tool_router/` as an independently importable Python package that implements the `#tool-selection` decision pattern.
2. THE package SHALL implement the `#tool-selection` pattern using the real Strands Decider 2B model and the documented Strands InterventionHandler integration mechanism.
3. THE package SHALL include the pattern implementation, a typed decision definition, an example integration, a README, unit tests, usage documentation, limitations documentation, and safety guidance.
4. THE package SHALL be importable and independently reusable without requiring the AegisPulse application code.
5. THE package SHALL include automated tests that verify the `#tool-selection` pattern in isolation.
6. THE package README SHALL reference the `#strands-decider-2b` and `#tool-selection` hackathon tags.

### Requirement 5: Bedrock Reasoning

**User Story:** As a demo viewer, I want Amazon Bedrock to interpret evidence and produce readable explanations, so that I can understand the agent's assessment in plain language.

#### Acceptance Criteria

1. THE Bedrock_Reasoner SHALL use Amazon Bedrock with a configurable supported model.
2. THE Bedrock_Reasoner SHALL resolve AWS credentials using the AWS default credential resolution chain.
3. WHEN evidence has been gathered, THE Bedrock_Reasoner SHALL produce a concise human-readable assessment of the evidence.
4. THE Bedrock_Reasoner SHALL generate hypotheses, human-readable explanations, post-incident summaries, and original-vs-replay comparisons.
5. THE Bedrock_Reasoner SHALL NOT override, alter, or bypass the Recovery_Tool selected by the Decider.
6. THE Bedrock_Reasoner SHALL NOT alter or override the Safety_Policy authorization outcome.
7. WHEN the configured Bedrock model is used, THE Bedrock_Reasoner SHALL verify the model's availability in the configured AWS region before invocation.
8. THE Bedrock_Reasoner SHALL treat Bedrock responses and retrieved text as untrusted input and SHALL validate them before use.
9. IF a Bedrock invocation returns an error or throttling response, THEN THE Bedrock_Reasoner SHALL record a structured error and continue the workflow without blocking the Decider decision.

### Requirement 6: Deterministic Safety Policy and Approval Gate

**User Story:** As a reliability engineer, I want a separate deterministic policy engine to authorize or block the Decider's recommendation, so that only safe simulated actions execute.

#### Acceptance Criteria

1. THE Safety_Policy SHALL operate as a deterministic policy engine separate from the Decider and SHALL authorize only Recovery_Tools present in the tool allowlist.
2. THE Safety_Policy SHALL authorize or block the candidate Recovery_Tool selected by the Decider, and neither the Decider nor the Bedrock_Reasoner SHALL override the Safety_Policy authorization outcome.
3. IF required evidence for a recommended action is missing, THEN THE Safety_Policy SHALL block execution and record a missing-evidence outcome.
4. THE Safety_Policy SHALL apply the configurable Confidence_Threshold, defaulting to 0.90, only to automatic state-changing actions.
5. IF the Decider confidence is below the Confidence_Threshold, THEN THE Safety_Policy SHALL block automatic execution of the state-changing Recovery_Tools `rollback_deployment`, `scale_out_service`, and `restart_unhealthy_tasks`.
6. IF the Decider confidence is below the Confidence_Threshold, THEN THE Safety_Policy SHALL permit the non-state-changing actions `investigate_further`, additional evidence collection, and `escalate_to_human`.
7. THE Safety_Policy SHALL always require explicit human approval through the Approval_Gate for the high-blast-radius operations `rollback_deployment` and `scale_out_service` regardless of the Decider confidence.
8. WHEN a high-blast-radius action is recommended, THE Approval_Gate SHALL require an explicit human approval decision before the Simulation_Engine executes the action.
9. THE Approval_Gate SHALL bind each approval to the exact incident identifier, action, action parameters, and Evidence_Snapshot identifier that were presented for approval.
10. THE Approval_Gate SHALL expire each approval after a configurable period defaulting to 120 seconds.
11. IF an approval's incident identifier, action, action parameters, or Evidence_Snapshot identifier does not match exactly what was approved, THEN THE Approval_Gate SHALL reject the approval and THE Simulation_Engine SHALL NOT execute the action.
12. IF an approval has expired, THEN THE Approval_Gate SHALL reject the approval and THE Simulation_Engine SHALL NOT execute the action.
13. IF the human approval decision is a rejection or no decision is recorded within the configured expiration period, THEN THE Approval_Gate SHALL block execution and record the pending action as not executed.
14. IF the Decider is unavailable, times out, returns a malformed response, or returns a tool outside the fixed option set, THEN THE Safety_Policy SHALL fail closed by blocking all automatic state-changing actions while permitting read-only investigation and human escalation.
15. WHEN the same authorized action is submitted more than once for the same pair of incident state and Correlation_ID, THE Safety_Policy SHALL execute the action at most once and return the original outcome on repeat.
16. THE Safety_Policy SHALL enforce a maximum of 3 failed attempts for a given recommended action, after which a retry-limit-exceeded outcome is recorded.
17. THE Safety_Policy SHALL write an audit log entry for each authorization decision including the Correlation_ID, the recommended tool, the confidence, the policy outcome, and the approval status.
18. THE Safety_Policy SHALL enforce that all remediation tools operate only against the Simulation_Engine.
19. THE Safety_Policy SHALL validate all external input before acting on it.

### Requirement 7: Counterfactual Incident Replay

**User Story:** As a demo viewer, I want to replay an incident with modified conditions, so that I can compare original and counterfactual recovery decisions.

#### Acceptance Criteria

1. WHEN a user replays an incident with modified conditions, THE Incident_Time_Machine SHALL re-run the incident workflow deterministically using the same fixed seed plus the modified conditions.
2. THE Incident_Time_Machine SHALL produce a comparison of the fields selected Recovery_Tool, confidence, and Safety_Policy outcome between the original and counterfactual recovery decisions, marking each field changed or unchanged.
3. THE Incident_Time_Machine SHALL label each Recovery_Tool selection and confidence value in the comparison as a real Decider model inference, and SHALL label each recovery outcome in the comparison as a simulated outcome.
4. THE Incident_Time_Machine SHALL demonstrate at least one of the five predefined scenarios in which the recommended Recovery_Tool changes between the original run and the replay.
5. WHERE replay conditions are identical and a fixed seed is used, THE Incident_Time_Machine SHALL reproduce both the selected tool and the Safety_Policy outcome of the original decision.
6. IF the modified replay conditions are invalid, THEN THE Incident_Time_Machine SHALL return a structured error and SHALL NOT start a replay.
7. THE Bedrock_Reasoner SHALL generate a human-readable summary of the original-vs-replay comparison that states whether the recommended tool changed and the reason.

### Requirement 8: Benchmark Harness

**User Story:** As a judge, I want a benchmark comparing Bedrock-only selection against Decider 2B selection, so that I can quantify what Decider 2B contributes.

#### Acceptance Criteria

1. THE Benchmark_Harness SHALL compare actual Bedrock-only recovery-tool selection against actual Decider 2B recovery-tool selection using identical incident states and identical option sets.
2. THE Benchmark_Harness SHALL evaluate at least 50 diverse synthetic evaluation cases distributed across all five predefined scenarios with a per-scenario minimum of at least 5 cases.
3. THE Benchmark_Harness SHALL execute at least 3 warm-up iterations per measured path, excluded from reported measurements, before recording timed inference measurements.
4. THE Benchmark_Harness SHALL measure end-to-end decision latency, model inference latency, tool-selection accuracy against the labeled expected outcomes defined in Requirement 1, unsafe-action recommendation rate, abstention-or-escalation rate, Bedrock input and output token usage, estimated variable inference cost where measurable, sample count, and hardware configuration.
5. THE Benchmark_Harness SHALL report p50 and p95 latency for each measured latency metric.
6. WHERE recorded confidence values are present, THE Benchmark_Harness SHALL report a confidence calibration measure.
7. THE Benchmark_Harness SHALL present measured cost separately from estimated cost.
8. THE Benchmark_Harness SHALL NOT fabricate performance results and SHALL NOT report any cost or performance saving that is not supported by a recorded measurement.
9. THE Benchmark_Harness SHALL execute both the Bedrock-only path and the Decider 2B path using real inference with no mocked or fabricated substitution.

### Requirement 9: Frontend Dashboard Screens

**User Story:** As a demo viewer, I want a mission-control dashboard with dedicated screens, so that I can observe and control the incident response visually.

#### Acceptance Criteria

1. THE AegisPulse frontend SHALL provide the Incident_Arena, Decision Observatory, Recovery Timeline, Incident_Time_Machine, Benchmark Lab, and Architecture & About screens.
2. THE frontend SHALL be built with React, TypeScript, Vite, and Tailwind using a dark mission-control theme.
3. THE Decision Observatory SHALL display the Decider choice probabilities, confidence indicators, selected tool, evidence inspection, and the Safety_Policy outcome.
4. THE Recovery Timeline SHALL display the agent execution timeline, recovery progress, and human approval controls.
5. WHEN a high-impact action awaits approval, THE frontend SHALL present approval and rejection controls to the user.
6. THE Benchmark Lab SHALL display latency and cost benchmark charts.
7. THE frontend SHALL distinguish illustrative sample data from real model inference and measured benchmark results.
8. THE frontend SHALL NOT display fabricated live predictions or invented metrics.
9. THE frontend SHALL provide accessible components, responsive layouts, loading states, and error handling.

### Requirement 10: Backend REST and Event Streaming API

**User Story:** As a frontend developer, I want a versioned REST API with event streaming, so that I can drive and observe the incident workflow.

#### Acceptance Criteria

1. THE AegisPulse backend SHALL be implemented with Python 3.11 or later and FastAPI.
2. THE backend SHALL expose the endpoints `GET /api/v1/health`, `GET /api/v1/scenarios`, `POST /api/v1/incidents`, `GET /api/v1/incidents/{id}`, `POST /api/v1/incidents/{id}/investigate`, `POST /api/v1/incidents/{id}/decide`, `POST /api/v1/incidents/{id}/approve`, `POST /api/v1/incidents/{id}/execute`, `POST /api/v1/incidents/{id}/replay`, `GET /api/v1/incidents/{id}/events`, `GET /api/v1/benchmarks`, and `POST /api/v1/benchmarks/run`.
3. THE backend SHALL define request and response models using Pydantic.
4. WHEN a request is received, THE backend SHALL attach a Correlation_ID and return structured errors on failure.
5. WHEN the client requests incident events, THE backend SHALL stream incident events for the identified incident.
6. WHEN a state-changing request is received, THE backend SHALL perform server-side authorization and validate the server-side incident state before applying the change.
7. IF a request fails validation, THEN THE backend SHALL return a structured error response identifying the invalid input.

### Requirement 11: Persistence of Decisions and Events

**User Story:** As a demo viewer, I want decisions and events persisted, so that I can inspect previous incident runs.

#### Acceptance Criteria

1. WHEN a decision is made, THE AegisPulse backend SHALL persist a Decision_Record capturing the input state, evidence references, the typed question, the available options, the selected option, the confidence, the model version identifier, the inference latency, the policy outcome, the approval status, and the execution result.
2. THE AegisPulse backend SHALL store each Decision_Record as an immutable record associated with the Evidence_Snapshot identifier and the Correlation_ID.
3. WHEN an incident event occurs, THE backend SHALL persist the event with a timestamp and Correlation_ID.
4. WHEN a user requests a previous incident, THE backend SHALL return the persisted Decision_Records and events for that incident.

### Requirement 12: Security and Secrets Handling

**User Story:** As a security reviewer, I want the system to follow secure-by-default practices, so that no real resources or secrets are exposed.

#### Acceptance Criteria

1. THE Strands_Agent SHALL operate without permissions to modify real production resources.
2. THE AegisPulse system SHALL NOT execute arbitrary shell commands or untrusted code.
3. THE AegisPulse system SHALL NOT perform unrestricted AWS operations.
4. THE AegisPulse backend SHALL perform server-side authorization on every state-changing endpoint before applying a change.
5. THE AegisPulse system SHALL validate all external input before processing.
6. THE AegisPulse system SHALL enforce an action allowlist and SHALL execute only allowlisted Recovery_Tools.
7. WHEN the same authorized action is submitted more than once for the same incident and Correlation_ID, THE AegisPulse system SHALL execute the action idempotently at most once.
8. THE AegisPulse system SHALL enforce approval expiration using the configurable expiration period defined in Requirement 6.
9. THE AegisPulse system SHALL maintain the audit log as an append-only, tamper-evident record.
10. THE AegisPulse system SHALL treat Bedrock responses and all retrieved or evidence text as untrusted input and SHALL NOT allow such text to directly trigger a state-changing tool call without passing the Decider selection, the deterministic Safety_Policy gate, and, where required, human approval.
11. THE AegisPulse system SHALL retrieve secrets from AWS Secrets Manager or AWS Systems Manager Parameter Store rather than from source code.
12. THE AegisPulse repository SHALL NOT contain committed secrets, keys, credentials, or sensitive logs.
13. WHEN a security-relevant event occurs, THE backend SHALL write a structured log entry for that event.

### Requirement 13: Testing and Release Gate

**User Story:** As a maintainer, I want comprehensive automated tests and a release gate, so that I can validate correctness before submission.

#### Acceptance Criteria

1. THE AegisPulse test suite SHALL include unit, integration, end-to-end, and property-based tests.
2. THE test suite SHALL cover Decider adapter response parsing, fixed-option validation, missing telemetry, contradictory evidence, low confidence, approval enforcement, approval binding and expiration, fail-closed behavior, invalid tool calls, repeated execution idempotency, state-transition integrity, replay reproducibility, Bedrock errors and throttling, Decider unavailability, API request validation, UI interaction, Docker startup, and AWS configuration.
3. FOR ALL Decider adapter responses, parsing then serializing then parsing SHALL produce an equivalent decision object (round-trip property).
4. THE continuous integration workflow SHALL run on GitHub Actions using mocked external services for all test categories except the release-gate checks.
5. THE backend code SHALL pass Pytest, Ruff, and mypy checks with zero errors and zero failures.
6. THE frontend code SHALL pass its configured frontend test suite with zero errors and zero failures.
7. THE release gate SHALL require a parsed in-set Recovery_Tool from a real, non-mocked Decider 2B inference AND a validated response from a real, non-mocked Bedrock invocation.
8. IF either required real call fails, THEN THE release gate SHALL block release and record a structured error.

### Requirement 14: AWS Deployment

**User Story:** As an operator, I want the system deployable to AWS with least-privilege and observability, so that I can host a secure demo.

#### Acceptance Criteria

1. THE AegisPulse system SHALL be packaged with Docker and Docker Compose.
2. WHERE AWS deployment is performed, THE deployment SHALL use an EC2 instance with model-compatible hardware for Decider 2B inference.
3. THE deployment SHALL attach an IAM instance profile scoped to least-privilege permissions that grant no permission capable of mutating a production AWS resource and that are limited to read, inference, and logging operations.
4. THE deployment SHALL send logs to CloudWatch.
5. THE deployment SHALL restrict inbound network access and SHALL serve traffic over TLS.
6. THE AegisPulse system SHALL require explicit human approval before any AWS deployment is performed.
7. THE deployment SHALL include mandatory resource tags for Environment, Application, Owner, CostCenter, Compliance, DataClassification, and ManagedBy.

### Requirement 15: Hackathon Submission Deliverables

**User Story:** As a hackathon participant, I want all required deliverables produced, so that the submission is complete and judgeable.

#### Acceptance Criteria

1. THE AegisPulse project SHALL provide a working local application that starts from documented commands.
2. THE project SHALL provide an AWS-deployable application configuration.
3. THE project SHALL provide a public GitHub-ready repository, an architecture diagram, a benchmark report, and at least 50 evaluation cases.
4. THE project SHALL provide a demo video script runnable in under 3 minutes, a Builder Center article draft, screenshots, and demo instructions.
5. THE project SHALL provide a license and third-party attribution review and a submission checklist.
6. THE project SHALL explicitly include the `#strands-decider-2b` and `#tool-selection` tags in submission materials.
7. WHEN the acceptance review is performed, THE project SHALL be considered complete only when the application starts from documented commands, five scenarios are available, real Decider 2B inference is demonstrated, real Bedrock inference is demonstrated, the Decider controls meaningful tool selection, policy gates are enforced, at least one scenario completes a simulated recovery, counterfactual replay works, benchmark results are reproducible, the reusable pattern imports independently, tests pass, no secrets are committed, and the public demo is completable in under 3 minutes.

### Requirement 16: Non-Functional Requirements (Judging Criteria and Demo Constraint)

**User Story:** As a hackathon judge, I want the product to excel against the judging criteria, so that it scores well on creativity, Decider usage, communication, and originality.

#### Acceptance Criteria

1. THE AegisPulse product SHALL present an interactive incident-response arena experience that demonstrates creativity and cool factor as the primary showcase (creativity criterion, 30%).
2. THE AegisPulse product SHALL demonstrate the Decider 2B model materially driving recovery-tool selection rather than only displaying a recommendation (Decider usage criterion, 30%).
3. THE AegisPulse product SHALL communicate the Decider contribution, policy decisions, and benchmark results through clear visual and written explanations (communication criterion, 25%).
4. THE AegisPulse product SHALL present an original incident-commander framing distinct from a generic Bedrock-only agent (originality criterion, 15%).
5. THE public demo of AegisPulse SHALL be completable in under 3 minutes.
6. WHEN the Decider confidence is at or above the configurable Confidence_Threshold defaulting to 0.90, THE Safety_Policy SHALL treat the recommendation as reliable for a short classification task and permit automatic execution of the selected state-changing Recovery_Tool subject to the approval rules in Requirement 6.
7. IF the Decider confidence is below the configurable Confidence_Threshold, THEN THE Safety_Policy SHALL block automatic execution of state-changing Recovery_Tools while permitting read-only investigation, additional evidence collection, and escalation.

### Requirement 17: MVP Scope and Delivery Priority

**User Story:** As a hackathon participant with a fixed deadline, I want a working end-to-end vertical slice prioritized first, so that the submission demonstrates real value before breadth features are completed.

#### Acceptance Criteria

1. THE AegisPulse MVP SHALL deliver real Decider 2B inference, real Bedrock integration, exactly one fully working incident recovery flow, and the human approval gate before the remaining four scenarios, advanced dashboard screens, or the full Benchmark_Harness are completed.
2. THE AegisPulse project SHALL deliver the remaining four predefined scenarios after the MVP vertical slice is demonstrably working.
3. THE AegisPulse project SHALL deliver the advanced dashboard screens after the MVP vertical slice is demonstrably working.
4. THE AegisPulse project SHALL deliver the full Benchmark_Harness after the MVP vertical slice is demonstrably working.
5. THE AegisPulse project SHALL treat the remaining four scenarios, the advanced dashboard screens, and the full Benchmark_Harness as phased delivery priorities that remain in scope.
