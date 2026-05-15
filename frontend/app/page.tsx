"use client";

import { useState } from "react";

const MODULES = [
  { name: "IntentOS", desc: "Chat → Structured Objectives" },
  { name: "TaskOS", desc: "Objectives → Executable Tasks" },
  { name: "AgentOS", desc: "Tasks → AI / Human / Vendor Assignment" },
  { name: "JobOS", desc: "Tasks → Paid Jobs & Bounties" },
  { name: "CompanyOS", desc: "Workflows → Departments & KPIs" },
  { name: "GovernanceOS", desc: "Approvals, Policies, Risk Gates" },
  { name: "ProofBook", desc: "Immutable Proof & Accountability" },
  { name: "SettlementOS", desc: "Payout Eligibility & Rails" },
  { name: "WorldBridge", desc: "Real-World Asset Connection" },
];

export default function Dashboard() {
  const [intent, setIntent] = useState("");
  const [logs, setLogs] = useState<string[]>([
    "[16:42:01] IntentOS: Intent ingested — 'I have a window and two hours free'",
    "[16:42:03] TaskOS: Objective created — 'Monetize window as ad inventory'",
    "[16:42:05] AgentOS: Assigned to Strategy Agent",
  ]);

  const submitIntent = async () => {
    if (!intent.trim()) return;
    setLogs((prev: string[]) => [`[${new Date().toLocaleTimeString()}] Submitting: "${intent}"`, ...prev]);
    // In production, POST to /api/v1/intents
    setIntent("");
  };

  return (
    <main className="min-h-screen p-6 md:p-10">
      <header className="mb-10">
        <h1 className="text-4xl font-bold gold-text tracking-tight">MEMBRA CompanyOS</h1>
        <p className="mt-2 text-membra-muted max-w-xl">
          The orchestration layer where AI builds, governs, and operates real-world companies
          through proof, permission, and local execution.
        </p>
      </header>

      {/* Intent Input */}
      <section className="card p-6 mb-8">
        <h2 className="text-lg font-semibold mb-3">Intent Ingestion</h2>
        <div className="flex gap-3">
          <input
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitIntent()}
            placeholder="I have a window, a car, two hours free, a drill, and a local network..."
            className="flex-1 bg-membra-surface border border-membra-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-membra-gold"
          />
          <button onClick={submitIntent} className="btn-primary">
            Ingest Intent
          </button>
        </div>
      </section>

      {/* Modules Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {MODULES.map((mod) => (
          <div key={mod.name} className="card p-5 hover:border-membra-gold transition-colors cursor-pointer">
            <h3 className="text-base font-semibold gold-text">{mod.name}</h3>
            <p className="text-sm text-membra-muted mt-1">{mod.desc}</p>
          </div>
        ))}
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
