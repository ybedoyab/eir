"use client";

import { useEffect, useState } from "react";

import { listAgents } from "@/services/api";
import type { AgentDescriptor } from "@/types";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentDescriptor[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section>
      <h1>Agents</h1>
      <p>Capability registry (local stand-in for Gemini Enterprise Agent Registry).</p>
      {error ? <p>API unavailable: {error}</p> : null}
      <ul>
        {agents.map((agent) => (
          <li key={agent.name}>
            <strong>{agent.name}</strong> [{agent.risk_level}] {agent.capabilities.join(", ")}
          </li>
        ))}
      </ul>
    </section>
  );
}
