"use client";

import { useState } from "react";
import {
  intentDrivenUI,
  schemaToComponent,
  predictiveOrchestrate,
  chatGovernance,
  verifyProof,
  agentSwarmProxy,
} from "../lib/llm";

const PATTERNS = [
  {
    id: "intent-ui",
    name: "IntentDrivenUI",
    desc: "Natural language mutates React state via backend LLM",
    color: "#c9a84c",
  },
  {
    id: "schema-component",
    name: "SchemaToComponent",
    desc: "SQLAlchemy schema auto-generates React components",
    color: "#e4c76b",
  },
  {
    id: "predict",
    name: "PredictiveOrchestration",
    desc: "LLM predicts next needs; backend pre-computes",
    color: "#60a5fa",
  },
  {
    id: "governance-chat",
    name: "ChatGovernance",
    desc: "Approve/reject via conversational LLM",
    color: "#f87171",
  },
  {
    id: "verify-proof",
    name: "MultimodalProof",
    desc: "Vision LLM verifies images as task proof",
    color: "#34d399",
  },
  {
    id: "swarm",
    name: "AgentSwarmProxy",
    desc: "One LLM proxy routes to multiple agents",
    color: "#a78bfa",
  },
];

export default function Dashboard() {
  const [logs, setLogs] = useState<string[]>([
    "[16:42:01] IntentDrivenUI: 'open task panel' → {task_panel: expanded}",
    "[16:42:03] PredictiveOrchestration: pre-fetched /api/v1/agents",
    "[16:42:05] AgentSwarmProxy: dispatched strategy + finance agents",
  ]);

  const [activePattern, setActivePattern] = useState<string>("intent-ui");
  const [inputText, setInputText] = useState("");
  const [output, setOutput] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const addLog = (msg: string) => {
    setLogs((prev: string[]) => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev].slice(0, 50));
  };

  const runPattern = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setOutput(null);
    addLog(`${activePattern}: invoking backend LLM bridge...`);

    try {
      let res: Record<string, unknown> = {};
      switch (activePattern) {
        case "intent-ui":
          res = await intentDrivenUI(inputText, "/");
          break;
        case "schema-component":
          res = await schemaToComponent("world_asset", [
            { name: "asset_type", type: "string", nullable: false },
            { name: "name", type: "string", nullable: false },
            { name: "price", type: "float", nullable: true },
          ]);
          break;
        case "predict":
          res = await predictiveOrchestrate("user_001", []);
          break;
        case "governance-chat":
          res = await chatGovernance(inputText, "0xdeadbeef");
          break;
        case "verify-proof":
          res = await verifyProof("task_001", inputText, "image/png");
          break;
        case "swarm":
          res = await agentSwarmProxy(inputText, "0xdeadbeef");
          break;
      }
      setOutput(res);
      addLog(`${activePattern}: response received (confidence ${(res.confidence as number) ?? 0.8})`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      addLog(`${activePattern}: ERROR — ${message}`);
      setOutput({ error: message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen p-6 md:p-10">
      <header className="mb-10">
        <h1 className="text-4xl font-bold gold-text tracking-tight">MEMBRA CompanyOS</h1>
        <p className="mt-2 text-membra-muted max-w-xl">
          The orchestration layer where AI builds, governs, and operates real-world companies
          through proof, permission, and local execution.
        </p>
        <p className="mt-1 text-xs text-membra-gold font-mono">6 Novel LLM Patterns — Frontend ↔ Backend</p>
      </header>

      {/* Pattern Selector */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        {PATTERNS.map((p) => (
          <button
            key={p.id}
            onClick={() => { setActivePattern(p.id); setOutput(null); }}
            className={`card p-4 text-left transition-all hover:scale-[1.02] ${
              activePattern === p.id ? "ring-2 ring-membra-gold" : ""
            }`}
          >
            <div className="text-xs font-bold mb-1" style={{ color: p.color }}>{p.name}</div>
            <div className="text-[11px] text-membra-muted leading-tight">{p.desc}</div>
          </button>
        ))}
      </section>

      {/* Active Pattern Panel */}
      <section className="card p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold gold-text">
            {PATTERNS.find((p) => p.id === activePattern)?.name}
          </h2>
          <span className="text-xs font-mono text-membra-muted bg-membra-surface px-2 py-1 rounded">
            POST /api/v1/llm/{activePattern}
          </span>
        </div>

        <div className="flex gap-3 mb-4">
          <input
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runPattern()}
            placeholder={
              activePattern === "intent-ui" ? "Say: 'open task panel' or 'show pending approvals'..."
              : activePattern === "schema-component" ? "Table name to generate component for..."
              : activePattern === "predict" ? "User ID for prediction..."
              : activePattern === "governance-chat" ? "Say: 'approve' or 'show pending'..."
              : activePattern === "verify-proof" ? "Paste base64 image data..."
              : "Message for agent swarm..."
            }
            className="flex-1 bg-membra-surface border border-membra-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-membra-gold"
          />
          <button
            onClick={runPattern}
            disabled={loading}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? "Processing..." : "Invoke LLM"}
          </button>
        </div>

        {output && (
          <div className="bg-membra-surface border border-membra-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-membra-muted mb-2">Response</h3>
            <pre className="text-xs font-mono text-green-400 overflow-x-auto">
              {JSON.stringify(output, null, 2)}
            </pre>
          </div>
        )}
      </section>

      {/* Live Logs */}
      <section className="card p-6">
        <h2 className="text-lg font-semibold mb-3">Orchestration Log</h2>
        <div className="bg-membra-surface border border-membra-border rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs">
          {logs.map((log: string, i: number) => (
            <div key={i} className="mb-1 text-green-400">{log}</div>
          ))}
        </div>
      </section>
    </main>
  );
}
