import React from "react";
// Decider choice-probability bars + confidence indicator.
export function ConfidenceView({ scores, selected, confidence }:
  { scores: Record<string, number>; selected: string; confidence: number }) {
  const entries = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const high = confidence >= 0.9;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-slate-300">Decider confidence</span>
        <span className={high ? "text-emerald-400" : "text-amber-400"}>
          {(confidence * 100).toFixed(1)}% {high ? "(reliable)" : "(confirm/escalate)"}
        </span>
      </div>
      {entries.map(([tool, p]) => (
        <div key={tool} className="mb-1">
          <div className="flex justify-between text-xs text-slate-400">
            <span className={tool === selected ? "font-semibold text-sky-300" : ""}>{tool}</span>
            <span>{(p * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 rounded bg-slate-800">
            <div className="h-2 rounded bg-sky-500" style={{ width: `${Math.round(p * 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
