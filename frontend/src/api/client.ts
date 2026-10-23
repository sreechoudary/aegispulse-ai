// Typed API client mirroring the frozen G1 contracts.
export const RECOVERY_TOOLS = [
  "rollback_deployment", "scale_out_service", "restart_unhealthy_tasks",
  "investigate_further", "escalate_to_human",
] as const;
export type RecoveryTool = (typeof RECOVERY_TOOLS)[number];

export interface Scenario { id: string; name: string; description: string; expected_outcome: RecoveryTool; }
export interface Telemetry { scenario_id: string; seed: number; service_health: string;
  context_signal?: string; series: Record<string, number[]>; summary: string; }
export interface InvestigateResult { evidence_snapshot_id: string; assessment: string; telemetry: Telemetry; }
export interface DecideResult {
  selected: RecoveryTool; confidence: number; policy_outcome: string; policy_reason: string;
  requires_approval: boolean; decider_health: string; expected_outcome: RecoveryTool;
  scores: Record<string, number>; latency_ms: number | null; model: string | null; assessment: string;
}
export interface ReplayDiff { field: string; original: any; replayed: any; changed: boolean; }
export interface ReplayResult { original_incident_id: string; replay_incident_id: string;
  conditions: Record<string, any>; tool_changed: boolean;
  labels: { decider: string; recovery: string }; diffs: ReplayDiff[]; }

const base = "/api/v1";
async function j<T>(r: Response): Promise<T> { if (!r.ok) throw new Error(await r.text()); return r.json(); }

export const api = {
  health: () => fetch(`${base}/health`).then(j<any>),
  scenarios: () => fetch(`${base}/scenarios`).then(j<Scenario[]>),
  createIncident: (scenario_id: string, seed = 42) =>
    fetch(`${base}/incidents`, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenario_id, seed }) }).then(j<any>),
  investigate: (id: string) =>
    fetch(`${base}/incidents/${id}/investigate`, { method: "POST" }).then(j<InvestigateResult>),
  decide: (id: string, evidence_snapshot_id: string) =>
    fetch(`${base}/incidents/${id}/decide`, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ evidence_snapshot_id }) }).then(j<DecideResult>),
  approve: (id: string, action: string, evidence_snapshot_id: string, decision: "approve" | "reject") =>
    fetch(`${base}/incidents/${id}/approve`, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ action, evidence_snapshot_id, decision }) }).then(j<any>),
  execute: (id: string) => fetch(`${base}/incidents/${id}/execute`, { method: "POST" }).then(j<any>),
  replay: (id: string, conditions: Record<string, any>) =>
    fetch(`${base}/incidents/${id}/replay`, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ conditions }) }).then(j<ReplayResult>),
  snapshot: (id: string) => fetch(`${base}/incidents/${id}`).then(j<any>),
  eventsUrl: (id: string) => `${base}/incidents/${id}/events`,
};
