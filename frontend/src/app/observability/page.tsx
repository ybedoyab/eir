"use client";

import { useEffect, useState } from "react";

import { listTraces } from "@/services/api";
import type { WorkflowTrace } from "@/types";

export default function ObservabilityPage() {
  const [traces, setTraces] = useState<WorkflowTrace[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTraces()
      .then(setTraces)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section>
      <h1>Observability</h1>
      <p>workflow_id, episode_id, trace_id, agent_name, event_type, status.</p>
      {error ? <p>API unavailable: {error}</p> : null}
      <ol>
        {traces.map((trace) => (
          <li key={trace.trace_id}>
            {trace.timestamp} — {trace.agent_name} / {trace.event_type} / {trace.status} (
            {trace.episode_id})
          </li>
        ))}
      </ol>
    </section>
  );
}
