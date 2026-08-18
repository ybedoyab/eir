"use client";

import { useEffect, useState } from "react";

import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { listAgents, getRuntimeStatus } from "@/services/api";
import type { AgentDescriptor, RuntimeStatus } from "@/types";

export default function AdminFleetPage() {
  const [agents, setAgents] = useState<AgentDescriptor[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);

  useEffect(() => {
    void Promise.all([listAgents(), getRuntimeStatus()]).then(([agentItems, status]) => {
      setAgents(agentItems);
      setRuntime(status);
    });
  }, []);

  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Operations" title="Fleet" />
      <Card>
        <CardHeader title="Runtime" description="Shared worker and adapter status." />
        <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
          <div>ADK mode: {runtime?.fleet.adk_mode ?? "—"}</div>
          <div>FHIR mode: {runtime?.fleet.fhir_mode ?? "—"}</div>
          <div>Event bus: {runtime?.fleet.event_bus ?? "—"}</div>
          <div>Gemini model: {runtime?.fleet.gemini_model ?? "—"}</div>
          <div>Agent Runtime: {runtime?.fleet.platform?.managed_agent_runtime_verified ? "MANAGED" : "UNVERIFIED"}</div>
          <div>Memory Bank: {runtime?.fleet.platform?.managed_memory_bank_verified ? "MANAGED" : "UNVERIFIED"}</div>
          <div>Agent Registry: {runtime?.fleet.platform?.managed_registry_verified ? "MANAGED" : "UNVERIFIED"}</div>
          <div>Agent Identity: {runtime?.fleet.platform?.managed_agent_identity_verified ? "MANAGED" : "UNVERIFIED"}</div>
          <div>Model Armor: {runtime?.content_guard.managed_model_armor_available ? "MANAGED" : "UNVERIFIED"}</div>
          <div>
            Observability:{" "}
            {runtime?.fleet.platform?.otel_cloud_trace_verified ||
            runtime?.fleet.platform?.cloud_logging_verified
              ? "GCP"
              : "UNVERIFIED"}
          </div>
        </dl>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        {agents.map((agent) => (
          <Card key={agent.name}>
            <CardHeader title={agent.name} description={agent.description} />
            <p className="text-xs text-slate-500">{agent.capabilities.join(" · ")}</p>
          </Card>
        ))}
      </div>
    </section>
  );
}
