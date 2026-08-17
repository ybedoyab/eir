"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
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
    <section>
      <PageHeader
        eyebrow="Fleet registry"
        title="Agents"
        description="Capability registry and risk posture for each recovery agent."
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      {loading ? (
        <Card>
          <p className="text-sm text-slate-500">Loading agents…</p>
        </Card>
      ) : agents.length === 0 ? (
        <EmptyState title="No agents registered" description="Bootstrap the agent registry via the API." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {agents.map((agent) => (
            <Card key={agent.name}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{agent.name}</h2>
                  <p className="mt-1 text-sm text-slate-500">v{agent.version}</p>
                </div>
                <Badge className="bg-slate-100 text-slate-700 ring-slate-200">{agent.risk_level}</Badge>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-600">{agent.description}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {agent.capabilities.map((capability) => (
                  <Badge
                    key={capability}
                    className="bg-teal-50 text-teal-700 ring-teal-100"
                  >
                    {capability}
                  </Badge>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
