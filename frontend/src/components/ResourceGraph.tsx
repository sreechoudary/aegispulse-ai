import React from "react";
import { Topology, GraphNode } from "../api/client";

// Layout on a 680 x 260 canvas. Node box is 150 wide; rightmost column starts at x=500,
// so it ends at 650 — safely inside the 680 viewBox (no right-side clipping).
const NODE_W = 150;
const NODE_H = 46;
const VB_W = 680;
const VB_H = 260;

const POS: Record<string, { x: number; y: number }> = {
  deploy: { x: 20, y: 30 },
  alb: { x: 20, y: 150 },
  svc: { x: 265, y: 95 },
  tasks: { x: 500, y: 30 },
  db: { x: 500, y: 165 },
};

const ICON: Record<string, string> = {
  alb: "\u2b16", service: "\u25c9", compute: "\u2637", database: "\u25d3", deployment: "\u2191",
};

function color(status: string) {
  return status === "critical"
    ? { stroke: "#f87171", fill: "#2b1414", text: "#fca5a5" }
    : { stroke: "#2f6f4f", fill: "#0f1f17", text: "#86efac" };
}

// edge endpoints: connect right-center of A to left-center of B
function edgePoints(a: { x: number; y: number }, b: { x: number; y: number }) {
  return { x1: a.x + NODE_W, y1: a.y + NODE_H / 2, x2: b.x, y2: b.y + NODE_H / 2 };
}

export function ResourceGraph({ topology }: { topology: Topology }) {
  const byId: Record<string, GraphNode> = Object.fromEntries(topology.nodes.map((n) => [n.id, n]));
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-300">
          Resource Graph
          <span className="rounded bg-amber-950 px-2 py-0.5 text-[10px] font-normal text-amber-300 border border-amber-800">SIMULATED topology</span>
          <span className="text-[10px] font-normal text-slate-500">affected resources highlighted</span>
        </h3>
        <span className={`text-xs ${topology.overall === "degraded" ? "text-amber-400" : "text-emerald-400"}`}>
          posture: {topology.overall}
        </span>
      </div>
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} preserveAspectRatio="xMidYMid meet"
           className="h-auto w-full" role="img"
           aria-label="Simulated resource graph with affected resources highlighted">
        {topology.edges.map((e, i) => {
          const a = POS[e.from], b = POS[e.to];
          if (!a || !b) return null;
          const hot = byId[e.from]?.status === "critical" && byId[e.to]?.status === "critical";
          const pts = edgePoints(a, b);
          return (
            <line key={i} x1={pts.x1} y1={pts.y1} x2={pts.x2} y2={pts.y2}
              stroke={hot ? "#f87171" : "#334155"} strokeWidth={hot ? 2.5 : 1.5}
              strokeDasharray={hot ? "0" : "4 3"} />
          );
        })}
        {topology.nodes.map((n) => {
          const p = POS[n.id]; if (!p) return null;
          const c = color(n.status);
          return (
            <g key={n.id}>
              <rect x={p.x} y={p.y} width={NODE_W} height={NODE_H} rx={8}
                fill={c.fill} stroke={c.stroke} strokeWidth={n.status === "critical" ? 2.5 : 1.5} />
              {n.status === "critical" && (
                <rect x={p.x} y={p.y} width={NODE_W} height={NODE_H} rx={8} fill="none"
                  stroke="#f87171" strokeWidth={2.5} opacity={0.5}>
                  <animate attributeName="opacity" values="0.15;0.6;0.15" dur="1.6s" repeatCount="indefinite" />
                </rect>
              )}
              <text x={p.x + 12} y={p.y + 20} fontSize="13" fill={c.text}>{ICON[n.kind] ?? "\u25a0"}</text>
              <text x={p.x + 32} y={p.y + 20} fontSize="12" fill="#e2e8f0">{n.label}</text>
              <text x={p.x + 12} y={p.y + 37} fontSize="10" fill="#94a3b8">{n.metric}</text>
            </g>
          );
        })}
      </svg>
      <p className="mt-1 text-[10px] text-slate-500">
        Red = affected (derived from real simulated telemetry). This is an illustrative map of the
        SIMULATED environment, not real AWS resource discovery.
      </p>
    </div>
  );
}
