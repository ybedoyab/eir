"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { listTraces } from "@/services/api";
import type { WorkflowTrace } from "@/types";

export default function ObservabilityPage() {
  const [traces, setTraces] = useState<WorkflowTrace[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTraces()
      .then(setTraces)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section>
      <PageHeader
        eyebrow="Workflow telemetry"
        title="Observability"
        description="Trace IDs, agent activity, and event status across the recovery loop."
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      <Card>
        <CardHeader
          title="Recent traces"
          description="workflow_id · episode_id · trace_id · agent_name · event_type · status"
        />
        {loading ? (
          <p className="text-sm text-slate-500">Loading traces…</p>
        ) : traces.length === 0 ? (
          <EmptyState
            title="No traces recorded"
            description="Run a recovery workflow to populate observability data."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2 font-medium">Time</th>
                  <th className="px-3 py-2 font-medium">Agent</th>
                  <th className="px-3 py-2 font-medium">Event</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Episode</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((trace) => (
                  <tr key={trace.trace_id} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-3 font-mono text-xs text-slate-500">{trace.timestamp}</td>
                    <td className="px-3 py-3 font-medium text-slate-800">{trace.agent_name}</td>
                    <td className="px-3 py-3 text-slate-700">{trace.event_type}</td>
                    <td className="px-3 py-3">
                      <Badge className="bg-slate-100 text-slate-700 ring-slate-200">{trace.status}</Badge>
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-500">{trace.episode_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </section>
  );
}
