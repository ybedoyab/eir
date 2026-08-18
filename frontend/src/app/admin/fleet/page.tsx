"use client";

import {
  Bot,
  Brain,
  CalendarDays,
  HeartPulse,
  ShieldCheck,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Card } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { platformStatus } from "@/lib/statusLabels";
import { getRuntimeStatus, listAgents } from "@/services/api";
import type { AgentDescriptor, RuntimeStatus } from "@/types";

const LOGICAL_FLEET: Array<{ name: string; description: string; icon: LucideIcon }> = [
  { name: "Patient Access", description: "Portal and conversational appointment access", icon: Users },
  { name: "Scheduling", description: "Slot search, booking, reschedule, and waitlist", icon: CalendarDays },
  { name: "Recovery / Outreach", description: "Longitudinal follow-up and check-ins", icon: HeartPulse },
  { name: "Risk", description: "Escalation signals from recovery responses", icon: ShieldCheck },
  { name: "Adherence", description: "Care-task follow-through", icon: HeartPulse },
  { name: "Records", description: "Synthetic FHIR read path", icon: Brain },
  { name: "Escalation", description: "Human review handoff", icon: Bot },
];

export default function AdminFleetPage() {
  const [agents, setAgents] = useState<AgentDescriptor[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTechnical, setShowTechnical] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [agentItems, status] = await Promise.all([listAgents(), getRuntimeStatus()]);
      setAgents(agentItems);
      setRuntime(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load fleet");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const platform = runtime?.fleet.platform;
  const gemini = runtime?.fleet.gemini_model ?? "Gemini 3.5 Flash";

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Operations"
        title="EIR Agent Fleet"
        description="7 coordinated capabilities. Managed governance active."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      {loading ? (
        <CardSkeleton rows={6} />
      ) : (
        <>
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Managed platform
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              <PlatformCard
                title="Patient Access Agent"
                status={platformStatus(platform?.managed_agent_runtime_verified, "Live")}
                detail={`Agent Runtime · ${gemini}`}
              />
              <PlatformCard
                title="Memory Bank"
                status={platformStatus(platform?.managed_memory_bank_verified, "Live")}
                detail="Cross-session context"
              />
              <PlatformCard
                title="Agent Registry"
                status={platformStatus(platform?.managed_registry_verified, "Live")}
                detail="eir-patient-access"
              />
              <PlatformCard
                title="Agent Identity"
                status={platformStatus(platform?.managed_agent_identity_verified, "Live")}
                detail="Least privilege"
              />
              <PlatformCard
                title="Agent Gateway"
                status={{
                  label: platform?.managed_agent_gateway_verified ? "Enforced" : "Unverified",
                  tone: platform?.managed_agent_gateway_verified ? "success" : "warning",
                }}
                detail="AGENT_TO_ANYWHERE"
              />
              <PlatformCard
                title="Model Armor"
                status={{
                  label: runtime?.content_guard.managed_model_armor_available ? "Active" : "Unverified",
                  tone: runtime?.content_guard.managed_model_armor_available ? "success" : "warning",
                }}
                detail="Managed content screening"
              />
              <PlatformCard
                title="Observability"
                status={{
                  label:
                    platform?.otel_cloud_trace_verified || platform?.cloud_logging_verified
                      ? "Active"
                      : "Unverified",
                  tone:
                    platform?.otel_cloud_trace_verified || platform?.cloud_logging_verified
                      ? "success"
                      : "warning",
                }}
                detail="Cloud Trace and Logging"
              />
            </div>
          </div>

          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Logical fleet
            </h2>
            <p className="mb-4 text-sm text-slate-600">
              These are coordinated capabilities, not separate ReasoningEngine deployments.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {LOGICAL_FLEET.map((agent) => {
                const Icon = agent.icon;
                const registered = agents.find((item) =>
                  item.name.toLowerCase().includes(agent.name.split(" ")[0].toLowerCase()),
                );
                return (
                  <Card key={agent.name}>
                    <div className="flex items-start gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-800">
                        <Icon aria-hidden className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="font-semibold text-slate-900">{agent.name}</p>
                        <p className="mt-1 text-sm text-slate-600">{agent.description}</p>
                        {registered ? (
                          <p className="mt-2 text-xs text-slate-500">{registered.capabilities.join(" · ")}</p>
                        ) : null}
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            className="text-sm font-medium text-teal-700"
            onClick={() => setShowTechnical((value) => !value)}
          >
            {showTechnical ? "Hide technical details" : "View technical details"}
          </button>
          {showTechnical && runtime ? (
            <Card>
              <dl className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                <div>ADK mode: {runtime.fleet.adk_mode}</div>
                <div>FHIR mode: {runtime.fleet.fhir_mode}</div>
                <div>Event bus: {runtime.fleet.event_bus}</div>
                <div>Gemini: {runtime.fleet.gemini_model}</div>
                <div>Armor template: {runtime.model_armor.template}</div>
                <div>Armor mode: {runtime.model_armor.mode}</div>
              </dl>
            </Card>
          ) : null}
        </>
      )}
    </section>
  );
}

function PlatformCard({
  title,
  status,
  detail,
}: {
  title: string;
  status: { label: string; tone: "success" | "warning" | "danger" | "info" | "neutral" | "brand" };
  detail: string;
}) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-900">{title}</p>
          <p className="mt-1 text-sm text-slate-600">{detail}</p>
        </div>
        <StatusBadge status={status} />
      </div>
    </Card>
  );
}
