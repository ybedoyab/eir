"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { listAgents } from "@/services/api";
import type { AgentDescriptor } from "@/types";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentDescriptor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Fleet registry"
        title="Agents"
        description="Capability registry and risk posture for each recovery agent."
        density="dense"
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      {loading ? (
        <CardSkeleton rows={5} />
      ) : agents.length === 0 ? (
        <EmptyState
          title="No agents registered"
          description="Bootstrap the agent registry via the API."
        />
      ) : (
        <div className="flex flex-col">
          <div className="grid grid-cols-[minmax(0,1fr)_88px] items-baseline gap-4 border-b border-rule-strong pb-2.5 md:grid-cols-[220px_minmax(0,1fr)_96px_88px]">
            <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
              Agent
            </span>
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.1em] text-muted md:block">
              Capabilities
            </span>
            <span className="hidden text-right font-mono text-[10px] uppercase tracking-[0.1em] text-muted md:block">
              Risk
            </span>
            <span className="text-right font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
              Version
            </span>
          </div>

          {agents.map((agent) => (
            <div
              key={agent.name}
              className="grid min-h-11 grid-cols-[minmax(0,1fr)_88px] items-center gap-4 border-b border-rule py-2 md:grid-cols-[220px_minmax(0,1fr)_96px_88px]"
            >
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate font-mono text-[12.5px] text-ink">{agent.name}</span>
                <span className="truncate text-[12.5px] text-secondary">{agent.description}</span>
              </span>
              <span className="hidden truncate font-mono text-[11.5px] text-muted md:block">
                {agent.capabilities.join(", ") || "none declared"}
              </span>
              <span className="hidden text-right font-mono text-[11.5px] uppercase tracking-[0.06em] text-secondary md:block">
                {agent.risk_level}
              </span>
              <span className="text-right font-mono text-[11.5px] text-muted">v{agent.version}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
