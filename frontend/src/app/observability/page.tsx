"use client";

import { useEffect, useMemo, useState } from "react";

import { CascadeWaterfall, HaltBanner, type CascadeStep } from "@/components/cascade/CascadeWaterfall";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/cn";
import { getRuntimeHistory, getRuntimeStatus, listTraces } from "@/services/api";
import type { AdkWorkerTelemetry, RuntimeStatus, WorkflowTrace } from "@/types";

const BLOCKED_STATUSES = new Set(["blocked", "failed", "denied"]);

function traceKind(trace: WorkflowTrace): CascadeStep["kind"] {
  if (BLOCKED_STATUSES.has(trace.status)) return "suppressed";
  return trace.agent_name && trace.agent_name !== "runtime" ? "agent" : "runtime";
}

function toSteps(traces: WorkflowTrace[]): CascadeStep[] {
  return [...traces]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map((trace) => ({
      id: `${trace.trace_id}-${trace.timestamp}`,
      label: `${trace.agent_name} · ${trace.event_type}`,
      detail: `episode ${trace.episode_id.slice(0, 8)} · ${trace.status}`,
      at: trace.timestamp,
      kind: traceKind(trace),
      halted: BLOCKED_STATUSES.has(trace.status),
    }));
}

export default function ObservabilityPage() {
  const [traces, setTraces] = useState<WorkflowTrace[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [history, setHistory] = useState<AdkWorkerTelemetry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

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

  const steps = useMemo(() => toSteps(traces), [traces]);
  const selected = steps.find((step) => step.id === selectedId) ?? steps[steps.length - 1] ?? null;
  const selectedTrace = traces.find(
    (trace) => `${trace.trace_id}-${trace.timestamp}` === selected?.id,
  );
  const selectedTelemetry = history.find((item) => item.trace_id === selectedTrace?.trace_id);
  const blocked = steps.filter((step) => step.halted);
  const armor = runtime?.model_armor;

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="font-serif text-[26px] font-medium leading-[1.2] tracking-[-0.015em] text-ink">
            Event cascade
          </h1>
          <p className="mt-1.5 max-w-[70ch] text-[13.5px] leading-[1.5] text-secondary">
            Laid out against the event timestamps themselves, not the fetch. Every step is a real
            handler result — the model never produced one.
          </p>
        </div>
        <div className="flex items-center gap-5 font-mono text-[12px] text-secondary">
          <span>
            steps <span className="text-ink">{steps.length}</span>
          </span>
          <span>
            depth guard <span className="text-ink">12</span>
          </span>
        </div>
      </header>

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      {loading ? (
        <CardSkeleton rows={6} />
      ) : steps.length === 0 ? (
        <EmptyState
          title="No traces recorded"
          description="Run a recovery workflow to populate the cascade."
        />
      ) : (
        <div className="grid items-start gap-7 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="flex min-w-0 flex-col gap-6">
            <CascadeWaterfall steps={steps} selectedId={selected?.id} onSelect={setSelectedId} />
            {blocked.length ? (
              <HaltBanner
                title="CASCADE HALTED"
                detail={`${blocked.length} step${blocked.length === 1 ? " was" : "s were"} blocked or suppressed. The workflow resumes only when a person answers.`}
              />
            ) : null}
          </div>

          {/* span detail */}
          <aside className="on-raised flex flex-col border-l border-rule bg-raised xl:sticky xl:top-6">
            <div className="flex flex-col gap-2 border-b border-rule px-6 pb-4 pt-5">
              <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                Selected step
              </span>
              <h2 className="font-mono text-[17px] font-medium text-ink">
                {selectedTrace?.event_type ?? "—"}
              </h2>
              <span className="font-mono text-[11.5px] text-muted">
                {selectedTrace
                  ? `${selectedTrace.agent_name} · trace ${selectedTrace.trace_id.slice(0, 8)}`
                  : "no step selected"}
              </span>
            </div>

            {selectedTrace ? (
              <dl className="grid grid-cols-[118px_minmax(0,1fr)] gap-x-3.5 gap-y-2 border-b border-rule px-6 py-4 font-mono text-[12px]">
                <dt className="text-muted">episode</dt>
                <dd className="truncate text-body">{selectedTrace.episode_id}</dd>
                <dt className="text-muted">workflow</dt>
                <dd className="truncate text-body">{selectedTrace.workflow_id}</dd>
                <dt className="text-muted">status</dt>
                <dd
                  className={cn(
                    BLOCKED_STATUSES.has(selectedTrace.status) ? "text-high" : "text-ok",
                  )}
                >
                  {selectedTrace.status}
                </dd>
                <dt className="text-muted">timestamp</dt>
                <dd className="text-body">{selectedTrace.timestamp}</dd>
              </dl>
            ) : null}

            {selectedTelemetry ? (
              <div className="flex flex-col gap-2.5 border-b border-rule px-6 py-4">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                  ADK run
                </span>
                <dl className="grid grid-cols-[118px_minmax(0,1fr)] gap-x-3.5 gap-y-2 font-mono text-[12px]">
                  <dt className="text-muted">model</dt>
                  <dd className="truncate text-body">{selectedTelemetry.model}</dd>
                  <dt className="text-muted">capability</dt>
                  <dd className="truncate text-body">{selectedTelemetry.capability}</dd>
                  <dt className="text-muted">tools invoked</dt>
                  <dd className="text-body">
                    {selectedTelemetry.tools_invoked.join(", ") || "none"}
                  </dd>
                  <dt className="text-muted">direct fallback</dt>
                  <dd className={selectedTelemetry.used_direct_fallback ? "text-warn" : "text-ok"}>
                    {String(selectedTelemetry.used_direct_fallback)}
                  </dd>
                </dl>
              </div>
            ) : null}

            {runtime ? (
              <div className="flex flex-col gap-2.5 border-b border-rule px-6 py-4">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                  Safety gate
                </span>
                <dl className="grid grid-cols-[118px_minmax(0,1fr)] gap-x-3.5 gap-y-2 font-mono text-[12px]">
                  <dt className="text-muted">armor mode</dt>
                  <dd className={armor?.mode === "managed" ? "text-ok" : "text-warn"}>
                    {armor?.mode ?? "unknown"}
                  </dd>
                  <dt className="text-muted">content guard</dt>
                  <dd
                    className={
                      runtime.content_guard.managed_model_armor_available
                        ? "text-ok"
                        : "text-warn"
                    }
                  >
                    {runtime.content_guard.adapter}
                  </dd>
                  <dt className="text-muted">last screening</dt>
                  <dd className="text-body">
                    {armor?.last_screening_success === null
                      ? "not run"
                      : String(armor?.last_screening_success)}
                  </dd>
                </dl>
              </div>
            ) : null}

            <div className="mt-auto flex flex-col gap-2 border-t border-rule-strong px-6 pb-5 pt-4">
              <span className="font-mono text-[10.5px] leading-[1.55] text-muted">
                Handler results come from Python, never from the model.
              </span>
              <span className="font-mono text-[10.5px] leading-[1.55] text-muted">
                Synthetic demo environment · no real patient data
              </span>
            </div>
          </aside>
        </div>
      )}

      {history.length ? (
        <section className="flex flex-col">
          <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
            <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
              Autonomous action history
            </h2>
            <span className="font-mono text-[10.5px] text-muted">sanitized worker hops</span>
          </div>
          {history.map((item) => (
            <div
              key={`${item.trace_id}-${item.timestamp}`}
              className="grid min-h-11 grid-cols-[200px_minmax(0,1fr)_120px] items-center gap-4 border-b border-rule"
            >
              <span className="truncate font-mono text-[12.5px] text-ink">
                {item.agent_name} · {item.capability}
              </span>
              <span className="truncate font-mono text-[11.5px] text-muted">
                {item.tools_invoked?.join(", ") || item.security_category || "no tools"}
              </span>
              <span
                className={cn(
                  "text-right font-mono text-[11.5px] uppercase tracking-[0.06em]",
                  item.success ? "text-ok" : "text-high",
                )}
              >
                {item.security_adapter ? item.security_adapter : item.success ? "ok" : "blocked"}
              </span>
            </div>
          ))}
        </section>
      ) : null}
    </>
  );
}
