"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { getRuntimeHistory, getRuntimeStatus, listTraces } from "@/services/api";
import type { AdkWorkerTelemetry, RuntimeStatus, WorkflowTrace } from "@/types";

function statusBadge(ok: boolean | null | undefined, okLabel: string, failLabel: string) {
  if (ok === true) {
    return <Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">{okLabel}</Badge>;
  }
  if (ok === false) {
    return <Badge className="bg-rose-50 text-rose-700 ring-rose-200">{failLabel}</Badge>;
  }
  return <Badge className="bg-slate-100 text-slate-600 ring-slate-200">Unknown</Badge>;
}

function FleetRuntime({ runtime }: { runtime: RuntimeStatus }) {
  const armor = runtime.model_armor;
  const fleet = runtime.fleet;
  const adkLive = fleet.adk_mode === "adk" && fleet.vertex_probe_success;

  return (
    <Card className="mb-6">
      <CardHeader
        title="Fleet Runtime"
        description="Shared production proof from API and worker telemetry."
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Gemini</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{fleet.gemini_model}</p>
          <p className="mt-1 text-xs text-slate-500">Location: {fleet.gemini_location}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">ADK</p>
          <div className="mt-2">{statusBadge(adkLive, "Live", "Offline")}</div>
          <p className="mt-2 text-xs text-slate-500">
            Direct fallback: {fleet.adk_allow_direct_fallback ? "Enabled" : "Disabled"}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Model Armor</p>
          <div className="mt-2">
            {armor.mode === "managed" ? (
              statusBadge(true, "Managed", "Unavailable")
            ) : armor.mode === "degraded" ? (
              <Badge className="bg-amber-50 text-amber-800 ring-amber-200">Degraded</Badge>
            ) : (
              statusBadge(false, "Managed", "Fallback")
            )}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            {armor.template || "regex"} · {armor.location || "local"}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Platform</p>
          <p className="mt-2 text-sm text-slate-800">Pub/Sub · FHIR · Scheduler</p>
          <p className="mt-1 text-xs text-slate-500">
            {fleet.event_bus} · {fleet.fhir_mode} · {fleet.runtime_region}
          </p>
        </div>
      </div>
    </Card>
  );
}

function LastAutonomousAction({ worker }: { worker: AdkWorkerTelemetry | null }) {
  if (!worker) {
    return (
      <Card className="mb-6">
        <CardHeader
          title="Last autonomous action"
          description="Waiting for the worker to record shared ADK telemetry."
        />
        <EmptyState title="No worker telemetry yet" description="Trigger a follow-up to populate proof." />
      </Card>
    );
  }

  return (
    <Card className="mb-6 border-teal-200 bg-teal-50/40">
      <CardHeader
        title="Last autonomous action"
        description="Latest shared worker ADK invocation (no PHI)."
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Agent</p>
          <p className="mt-1 text-sm font-medium text-slate-900">{worker.agent_name}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Capability</p>
          <p className="mt-1 text-sm font-medium text-slate-900">{worker.capability}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Worker</p>
          <p className="mt-1 text-sm font-medium text-slate-900">{worker.service}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Tools invoked</p>
          <p className="mt-1 text-sm text-slate-800">{worker.tools_invoked.join(", ") || "None"}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Outcome</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {statusBadge(worker.success, "Success", "Failed")}
            {statusBadge(!worker.used_direct_fallback, "No fallback", "Fallback used")}
          </div>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Timestamp</p>
          <p className="mt-1 font-mono text-xs text-slate-600">{worker.timestamp}</p>
        </div>
      </div>
    </Card>
  );
}

function AutonomousHistory({ items }: { items: AdkWorkerTelemetry[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <Card className="mb-6">
      <CardHeader
        title="Autonomous action history"
        description="Latest sanitized worker hops — outreach, risk, escalation, and security blocks."
      />
      <ol className="space-y-2">
        {items.map((item) => (
          <li
            key={`${item.trace_id}-${item.timestamp}`}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2"
          >
            <div>
              <p className="text-sm font-medium text-slate-900">
                {item.agent_name} · {item.capability}
              </p>
              <p className="text-xs text-slate-500">
                {item.tools_invoked?.join(", ") || item.security_category || "no tools"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {item.security_adapter ? (
                <Badge className="bg-rose-50 text-rose-700 ring-rose-200">
                  {item.security_adapter}
                </Badge>
              ) : null}
              {statusBadge(item.success, "OK", "Blocked")}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export default function ObservabilityPage() {
  const [traces, setTraces] = useState<WorkflowTrace[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [history, setHistory] = useState<AdkWorkerTelemetry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([listTraces(), getRuntimeStatus(), getRuntimeHistory(25)])
      .then(([traceRows, runtimeStatus, historyPayload]) => {
        setTraces(traceRows);
        setRuntime(runtimeStatus);
        setHistory(historyPayload.items);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section>
      <PageHeader
        eyebrow="Operations"
        title="Observability"
        description="System status, recent agent actions, and security decisions. Trace IDs stay secondary."
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      {loading && !runtime ? <CardSkeleton rows={4} /> : null}
      {runtime ? <FleetRuntime runtime={runtime} /> : null}
      {runtime ? <LastAutonomousAction worker={runtime.adk_worker} /> : null}
      <AutonomousHistory items={history} />

      <Card>
        <CardHeader
          title="Trace details"
          description="Technical identifiers for judges. Prompt and transcript content is never shown."
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
