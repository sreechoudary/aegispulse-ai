import React, { useEffect, useState } from "react";
import { api, Scenario, DecideResult, InvestigateResult, ReplayResult } from "./api/client";
import { ConfidenceView } from "./components/ConfidenceView";
import { ResourceGraph } from "./components/ResourceGraph";

type Phase = "idle" | "investigating" | "assessing" | "deciding" | "awaiting-approval"
  | "ready" | "recovered" | "blocked" | "error";

const HEALTH_COLOR: Record<string, string> = {
  healthy: "text-emerald-400", degraded: "text-amber-400", down: "text-red-400",
};

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [deciderUp, setDeciderUp] = useState<boolean | null>(null);
  const [bedrockOn, setBedrockOn] = useState<boolean | null>(null);
  const [incidentId, setIncidentId] = useState("");
  const [activeScenario, setActiveScenario] = useState<string>("");
  const [evidence, setEvidence] = useState("");
  const [inv, setInv] = useState<InvestigateResult | null>(null);
  const [decision, setDecision] = useState<DecideResult | null>(null);
  const [recovery, setRecovery] = useState<any>(null);
  const [replay, setReplay] = useState<ReplayResult | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [timeline, setTimeline] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const poll = () => api.health()
      .then((h: any) => { setApiUp(true); setDeciderUp(!!h.decider_online); setBedrockOn(!!h.bedrock_enabled); })
      .catch(() => { setApiUp(false); setDeciderUp(false); });
    poll();
    api.scenarios().then(setScenarios).catch(() => setApiUp(false));
    const t = setInterval(poll, 5000);
    return () => clearInterval(t);
  }, []);

  function log(msg: string) { setTimeline((t) => [...t, `${new Date().toLocaleTimeString()}  ${msg}`]); }

  async function launch(id: string) {
    try {
      setError(""); setDecision(null); setRecovery(null); setReplay(null); setTimeline([]);
      setActiveScenario(id);
      setPhase("investigating"); log(`Launching ${id}`);
      const incident = await api.createIncident(id); setIncidentId(incident.incident_id);
      log(`Incident ${incident.incident_id} · health=${incident.telemetry.service_health}`);
      setPhase("assessing");
      const investigation = await api.investigate(incident.incident_id);
      setInv(investigation); setEvidence(investigation.evidence_snapshot_id);
      log(`Evidence gathered · Bedrock assessing…`);
      setPhase("deciding");
      const dec = await api.decide(incident.incident_id, investigation.evidence_snapshot_id);
      setDecision(dec);
      log(`Decider selected ${dec.selected} (${(dec.confidence * 100).toFixed(1)}%) in ${dec.latency_ms?.toFixed(0)}ms`);
      log(`Policy: ${dec.policy_outcome} (${dec.policy_reason})`);
      setPhase(dec.requires_approval ? "awaiting-approval" :
        dec.policy_outcome === "Blocked" || dec.policy_outcome === "FailedClosed" ? "blocked" : "ready");
    } catch (e: any) { setError(String(e?.message ?? e)); setPhase("error"); }
  }

  async function approveAndRun() {
    if (!decision) return;
    try {
      await api.approve(incidentId, decision.selected, evidence, "approve");
      log(`Human approved ${decision.selected}`);
      const ex = await api.execute(incidentId); setRecovery(ex.recovery);
      log(`Recovered (simulated) · MTTR ${ex.recovery.mttr_seconds}s`); setPhase("recovered");
    } catch (e: any) { setError(String(e?.message ?? e)); setPhase("error"); }
  }

  async function runReplay() {
    try {
      const r = await api.replay(incidentId, { error_rate_multiplier: 0.05 });
      setReplay(r);
      log(`Replay: tool_changed=${r.tool_changed}`);
    } catch (e: any) { setError(String(e?.message ?? e)); }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/60 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-sky-300">AegisPulse AI</h1>
            <p className="text-sm text-slate-400">Detect. Decide. Defend. — Autonomous Incident Commander</p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className={apiUp === null ? "text-slate-500" : apiUp ? "text-emerald-400" : "text-red-400"}>
              {apiUp === null ? "connecting…" : apiUp ? "● backend" : "● backend offline"}
            </span>
            <span className={deciderUp == null ? "text-slate-500" : deciderUp ? "text-emerald-400" : "text-red-400"}
              title={deciderUp ? "Strands Decider 2B reachable" : "Decider server DOWN — scenarios will fall back to investigate_further"}>
              {deciderUp == null ? "" : deciderUp ? "● Decider 2B" : "● Decider offline"}
            </span>
            <span className={bedrockOn ? "text-emerald-400" : "text-slate-500"}
              title={bedrockOn ? "Amazon Bedrock assessment enabled" : "Bedrock disabled (AEGIS_ENABLE_BEDROCK=0)"}>
              {bedrockOn == null ? "" : bedrockOn ? "● Bedrock" : "○ Bedrock off"}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-xs">
          <span className="font-semibold text-slate-300">What is live:</span>
          <span className="rounded bg-sky-950 px-2 py-0.5 text-sky-300 border border-sky-800">REAL — Strands Decider 2B inference</span>
          <span className="rounded bg-sky-950 px-2 py-0.5 text-sky-300 border border-sky-800">REAL — Amazon Bedrock reasoning</span>
          <span className="rounded bg-amber-950 px-2 py-0.5 text-amber-300 border border-amber-800">SIMULATED — telemetry, topology &amp; remediation</span>
          <span className="text-slate-500">· no real infrastructure is ever modified</span>
        </div>
        {error && <div className="rounded border border-red-700 bg-red-950/50 p-3 text-sm text-red-300">Error: {error}</div>}

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Incident Arena</h2>
            {activeScenario && (
              <span className="text-xs text-slate-400">
                Running: <span className="font-semibold text-sky-300">{scenarios.find((x) => x.id === activeScenario)?.name ?? activeScenario}</span>
                {incidentId && <span className="text-slate-500"> · {incidentId}</span>}
              </span>
            )}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {scenarios.map((s) => {
              const active = s.id === activeScenario;
              return (
                <button key={s.id} onClick={() => launch(s.id)} aria-pressed={active}
                  className={`group rounded-lg border p-3 text-left transition ${
                    active
                      ? "border-sky-400 bg-sky-950/40 ring-2 ring-sky-500/60 shadow-lg shadow-sky-900/30"
                      : "border-slate-700 bg-slate-900 hover:border-sky-600 hover:bg-slate-800"
                  }`}>
                  <div className="flex items-center justify-between">
                    <div className={`font-medium ${active ? "text-sky-300" : "text-slate-100 group-hover:text-sky-300"}`}>{s.name}</div>
                    {active && <span className="rounded-full bg-sky-500 px-2 py-0.5 text-[10px] font-semibold text-slate-950">SELECTED</span>}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{s.description}</div>
                </button>
              );
            })}
          </div>
        </section>

        {inv?.telemetry?.topology && (
          <section>
            <ResourceGraph topology={inv.telemetry.topology} />
          </section>
        )}

        {phase !== "idle" && (
          <section className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-300">Agent Investigation Timeline</h3>
              <ol className="space-y-1 text-xs text-slate-400">
                {timeline.map((t, i) => <li key={i} className="font-mono">{t}</li>)}
              </ol>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-300">Bedrock Assessment <span className="text-[10px] text-sky-500">REAL inference</span></h3>
              {inv?.assessment ? <p className="text-sm text-slate-300">{inv.assessment}</p>
                : <p className="text-xs text-slate-500">{phase === "assessing" ? "Assessing…" : "—"}</p>}
              {inv?.telemetry && (
                <p className="mt-3 text-xs text-slate-500">
                  Health: <span className={HEALTH_COLOR[inv.telemetry.service_health] ?? ""}>{inv.telemetry.service_health}</span>
                  {inv.telemetry.context_signal ? ` · ${inv.telemetry.context_signal}` : ""}
                </p>
              )}
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-300">Decision Observatory <span className="text-[10px] text-sky-500">REAL Decider 2B</span></h3>
              {decision ? (
                <>
                  <ConfidenceView scores={decision.scores && Object.keys(decision.scores).length ? decision.scores : { [decision.selected]: decision.confidence }}
                    selected={decision.selected} confidence={decision.confidence} />
                  <p className="mt-2 text-xs text-slate-400">
                    latency <span className="text-slate-200">{decision.latency_ms?.toFixed(0)} ms</span> · model {decision.model}
                  </p>
                  <p className="mt-1 text-xs">
                    Policy gate: <span className="font-semibold text-amber-300">{decision.policy_outcome}</span>
                    <span className="text-slate-500"> ({decision.policy_reason})</span>
                  </p>
                </>
              ) : <p className="text-xs text-slate-500">{phase === "deciding" ? "Deciding…" : "—"}</p>}
            </div>
          </section>
        )}

        {decision && (
          <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-300">Recovery Timeline</h3>
            {phase === "awaiting-approval" && (
              <div className="flex items-center gap-3">
                <span className="text-amber-300">High-blast-radius action requires human approval.</span>
                <button onClick={approveAndRun} className="rounded bg-amber-600 px-4 py-2 font-semibold text-slate-950 hover:bg-amber-500">
                  Approve simulated {decision.selected}
                </button>
              </div>
            )}
            {phase === "blocked" && <p className="text-red-300">Blocked by deterministic policy — no execution.</p>}
            {recovery && (
              <div className="rounded border border-emerald-700 bg-emerald-950/40 p-3">
                <p className="font-semibold text-emerald-400">✓ Recovered (simulated)</p>
                <p className="text-sm text-slate-300">tool {recovery.tool} · MTTR {recovery.mttr_seconds}s · {recovery.service_impact}</p>
              </div>
            )}
          </section>
        )}

        {recovery && (
          <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300">Incident Time Machine</h3>
              <button onClick={runReplay} className="rounded border border-sky-700 bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700">
                Replay with 95% lower error rate
              </button>
            </div>
            {replay ? (
              <div className="text-sm">
                <p className="mb-2 text-slate-400">tool changed: <span className={replay.tool_changed ? "text-amber-300" : "text-slate-300"}>{String(replay.tool_changed)}</span>
                  {" "}· <span className="text-[10px] text-sky-500">{replay.labels.decider}</span></p>
                <table className="w-full text-xs">
                  <thead><tr className="text-slate-500"><th className="text-left">field</th><th className="text-left">original</th><th className="text-left">replayed</th><th>changed</th></tr></thead>
                  <tbody>
                    {replay.diffs.map((d) => (
                      <tr key={d.field} className="border-t border-slate-800">
                        <td className="py-1 text-slate-400">{d.field}</td>
                        <td className="text-slate-300">{String(d.original)}</td>
                        <td className="text-slate-300">{String(d.replayed)}</td>
                        <td className={`text-center ${d.changed ? "text-amber-300" : "text-slate-600"}`}>{d.changed ? "✓" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-xs text-slate-500">Replay the incident with modified evidence to compare decisions.</p>}
          </section>
        )}
      </main>

      <footer className="border-t border-slate-800 px-6 py-3 text-center text-xs text-slate-500">
        Decider predictions &amp; confidence are REAL model inference. Infrastructure metrics &amp; recovery outcomes are SIMULATED.
      </footer>
    </div>
  );
}
