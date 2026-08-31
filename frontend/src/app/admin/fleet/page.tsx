"use client";

import { useEffect, useState } from "react";

import { HaltBanner } from "@/components/cascade/CascadeWaterfall";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatCard, StatStrip } from "@/components/ui/StatCard";
import { cn } from "@/lib/cn";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { voiceProviderLabel } from "@/lib/demoStory";
import { formatWait } from "@/lib/format";
import { getRuntimeStatus, listAgents, listReviews, listTraces } from "@/services/api";
import type { AgentDescriptor, HumanReview, RuntimeStatus, WorkflowTrace } from "@/types";

type AdapterState = "real" | "fallback" | "unknown";

interface AdapterRow {
  name: string;
  state: AdapterState;
  detail: string;
}

const FLEET_COLUMNS = ["Agent", "Granted capabilities", "Risk", "Version"] as const;
const RECENT_TRACE_LIMIT = 8;

const ADAPTER_TONE: Record<AdapterState, string> = {
  real: "text-ok",
  fallback: "text-warn",
  unknown: "text-muted",
};

function voiceState(voiceAvailable: boolean, realProvider: boolean): AdapterState {
  if (!voiceAvailable) return "unknown";
  if (realProvider) return "real";
  return "fallback";
}

function videoState(configured: boolean, lastSuccess: boolean | null | undefined): AdapterState {
  if (!configured) return "unknown";
  if (lastSuccess === false) return "fallback";
  return "real";
}

function videoDetail(video: RuntimeStatus["fleet"]["recovery_video"]): string {
  if (!video?.configured) return "disabled";
  if (video.last_error) return `${video.storage?.backend ?? "veo"} · ${video.last_error}`;
  return `${video.adapter} · ${video.storage?.backend ?? "unknown"}`;
}

function blockingCapability(review: HumanReview): string {
  return review.pending_capability?.trim() || review.capability?.trim() || "Pending capability";
}

function adapterRows(runtime: RuntimeStatus | null): AdapterRow[] {
  if (!runtime) return [];
  const fleet = runtime.fleet;
  const voice = fleet.voice;
  const armorReal = runtime.content_guard.managed_model_armor_available === true;
  const voiceReal = voice?.active_provider === "voximplant";
  const video = fleet.recovery_video;
  return [
    {
      name: "event_bus",
      state: fleet.event_bus === "pubsub" ? "real" : "fallback",
      detail: fleet.event_bus,
    },
    {
      name: "fhir",
      state: fleet.fhir_mode === "gcp" ? "real" : "fallback",
      detail: fleet.fhir_mode === "gcp" ? "healthcare" : "local mocks",
    },
    {
      name: "adk_runner",
      state: fleet.adk_mode === "adk" ? "real" : "fallback",
      detail: fleet.adk_allow_direct_fallback ? `${fleet.adk_mode} · direct allowed` : fleet.adk_mode,
    },
    {
      name: "content_guard",
      state: armorReal ? "real" : "fallback",
      detail: runtime.content_guard.adapter,
    },
    {
      name: "model_armor",
      state: runtime.model_armor.available ? "real" : "fallback",
      detail: runtime.model_armor.mode,
    },
    {
      name: "voice",
      state: voiceState(Boolean(voice), voiceReal),
      detail: voiceProviderLabel(voice?.active_provider).toLowerCase(),
    },
    {
      name: "recovery_video",
      state: videoState(Boolean(video?.configured), video?.last_success),
      detail: videoDetail(video),
    },
  ];
}

export default function AdminFleetPage() {
  const [agents, setAgents] = useState<AgentDescriptor[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [traces, setTraces] = useState<WorkflowTrace[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [agentItems, status, traceItems, reviewItems] = await Promise.all([
        listAgents(),
        getRuntimeStatus(),
        listTraces(),
        listReviews(true),
      ]);
      setAgents(agentItems);
      setRuntime(status);
      setTraces(traceItems);
      setReviews(reviewItems);
      setRefreshedAt(new Date());
    } catch (err) {
      setError(getErrorMessage(err, ERROR_MESSAGES.fleet));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const adapters = adapterRows(runtime);
  const degraded = adapters.filter((row) => row.state === "fallback");
  const recent = [...traces]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, RECENT_TRACE_LIMIT);
  const oldestReview = reviews.length
    ? reviews.reduce((oldest, item) =>
        new Date(item.created_at) < new Date(oldest.created_at) ? item : oldest,
      )
    : null;

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="font-serif text-[1.6875rem] font-medium leading-[1.2] tracking-[-0.015em] text-ink">
            Agent fleet
          </h1>
          <p className="mt-1.5 text-[13.5px] leading-[1.5] text-secondary">
            {agents.length} capability-routed agents.{" "}
            {degraded.length
              ? `${degraded.length} adapter${degraded.length === 1 ? " is" : "s are"} on a fallback — the runtime is saying so rather than hiding it.`
              : "Every adapter is reporting real."}
          </p>
        </div>
        <Button
          variant="ghost"
          onClick={() => void refresh()}
          className="px-3 font-mono text-[0.75rem] font-normal text-muted"
        >
          <Icon name="refresh" size={14} />
          {refreshedAt
            ? `refreshed ${refreshedAt.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`
            : "refresh"}
        </Button>
      </header>

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <CardSkeleton rows={6} />
      ) : (
        <div className="grid gap-7 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="flex min-w-0 flex-col gap-6">
            <StatStrip className="sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label="Reviews waiting"
                value={reviews.length}
                tone={reviews.length ? "high" : "ink"}
                hint={
                  oldestReview
                    ? `oldest ${formatWait(oldestReview.created_at).replace(" waiting", "")}`
                    : "nothing parked"
                }
              />
              <StatCard
                label="Registered agents"
                value={agents.length}
                hint="first match by registration order"
              />
              <StatCard
                label="Traces recorded"
                value={traces.length}
                hint="cascade depth guard drops at 12"
              />
              <StatCard
                label="Adapters degraded"
                value={degraded.length}
                tone={degraded.length ? "warn" : "ok"}
                hint={
                  degraded.length
                    ? `${degraded[0].name} on fallback`
                    : "every adapter is the real thing"
                }
              />
            </StatStrip>

            <section className="flex flex-col">
              <div className="flex items-baseline justify-between gap-4 pb-2">
                <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                  Registry
                </h2>
                <span className="font-mono text-[10.5px] text-muted">
                  first match by registration order
                </span>
              </div>
              <div className="hidden grid-cols-[168px_minmax(0,1fr)_96px_96px] gap-4 border-b border-rule-strong pb-2 sm:grid">
                {FLEET_COLUMNS.map((column) => (
                  <span
                    key={column}
                    className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted"
                  >
                    {column}
                  </span>
                ))}
              </div>
              {agents.map((agent) => (
                <div
                  key={agent.name}
                  className="grid min-h-11 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 border-b border-rule py-2 sm:grid-cols-[168px_minmax(0,1fr)_96px_96px] sm:py-0"
                  title={agent.description}
                >
                  <span className="truncate text-[0.875rem] font-medium text-ink">{agent.name}</span>
                  <span className="col-span-2 truncate font-mono text-[0.75rem] text-secondary sm:col-span-1">
                    {agent.capabilities.join(" · ")}
                  </span>
                  <span className="col-start-2 row-start-1 text-right font-mono text-[0.75rem] text-secondary sm:col-start-auto sm:row-start-auto sm:text-left">
                    {agent.risk_level}
                  </span>
                  <span className="hidden font-mono text-[0.75rem] text-muted sm:block">
                    {agent.version}
                  </span>
                </div>
              ))}
            </section>

            <section className="flex flex-col">
              <div className="flex items-baseline justify-between gap-4 pb-2">
                <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                  Adapters
                </h2>
                <span className="font-mono text-[10.5px] text-muted">live from /health</span>
              </div>
              <div className="grid border-t border-rule-strong sm:grid-cols-2 lg:grid-cols-3">
                {adapters.map((row) => (
                  <div
                    key={row.name}
                    className={cn(
                      "flex min-h-10 items-center justify-between gap-3 border-b border-rule px-4 first:pl-0",
                      row.state === "fallback" && "bg-raised",
                    )}
                  >
                    <span className="font-mono text-[12.5px] text-body">{row.name}</span>
                    <span
                      className={cn(
                        "font-mono text-[0.75rem] uppercase tracking-[0.06em]",
                        ADAPTER_TONE[row.state],
                      )}
                    >
                      {row.state} · {row.detail}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {runtime ? (
              <details className="group border-t border-rule pt-3">
                <summary className="focus-ink flex min-h-11 cursor-pointer list-none items-center gap-2 font-mono text-[0.75rem] uppercase tracking-[0.1em] text-secondary hover:text-ink">
                  <Icon
                    name="chevronDown"
                    size={14}
                    className="transition-transform group-open:rotate-180"
                  />
                  Technical detail
                </summary>
                <dl className="grid grid-cols-[168px_minmax(0,1fr)] gap-x-4 gap-y-2 pb-3 pt-2 font-mono text-[0.75rem]">
                  <dt className="text-muted">gemini model</dt>
                  <dd className="text-body">{runtime.fleet.gemini_model}</dd>
                  <dt className="text-muted">gemini location</dt>
                  <dd className="text-body">{runtime.fleet.gemini_location}</dd>
                  <dt className="text-muted">runtime region</dt>
                  <dd className="text-body">{runtime.fleet.runtime_region}</dd>
                  <dt className="text-muted">workflow subscriber</dt>
                  <dd className="text-body">{runtime.fleet.workflow_subscriber}</dd>
                  <dt className="text-muted">armor template</dt>
                  <dd className="text-body">{runtime.model_armor.template || "—"}</dd>
                  <dt className="text-muted">armor location</dt>
                  <dd className="text-body">{runtime.model_armor.location || "—"}</dd>
                </dl>
              </details>
            ) : null}
          </div>

          <aside className="eir-surface on-raised flex h-fit flex-col self-start overflow-hidden bg-raised">
            <div className="flex items-center justify-between gap-3 border-b border-rule-strong px-5 pb-3 pt-5">
              <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-secondary">
                Event stream
              </span>
              <span className="inline-flex items-center gap-2 font-mono text-[10.5px] tracking-[0.06em] text-accent">
                <span className="h-1.5 w-1.5 bg-accent" aria-hidden />
                LIVE
              </span>
            </div>
            {recent.length ? (
              recent.map((trace) => (
                <div
                  key={`${trace.trace_id}-${trace.timestamp}`}
                  className="flex flex-col gap-[3px] border-b border-rule px-5 py-2.5"
                >
                  <div className="flex items-baseline justify-between gap-2.5">
                    <span className="truncate font-mono text-[12.5px] text-ink">
                      {trace.event_type}
                    </span>
                    <span
                      className={cn(
                        "shrink-0 font-mono text-[0.75rem]",
                        trace.status === "blocked" || trace.status === "failed"
                          ? "text-high"
                          : "text-secondary",
                      )}
                    >
                      {trace.status}
                    </span>
                  </div>
                  <span className="truncate font-mono text-[0.75rem] text-muted">
                    {new Date(trace.timestamp).toLocaleTimeString()} · {trace.agent_name}
                  </span>
                </div>
              ))
            ) : (
              <p className="px-5 py-4 text-[0.8125rem] text-muted">No traces recorded yet.</p>
            )}

            {oldestReview ? (
              <HaltBanner
                className="m-5"
                title="CASCADE HALTED"
                detail={`${blockingCapability(oldestReview)} is a blocking capability. Next events suppressed, review parked for a clinician.`}
                held={formatWait(oldestReview.created_at).replace(" waiting", "")}
              />
            ) : null}

            <div className="mt-auto border-t border-rule px-5 py-4">
              <span className="font-mono text-[10.5px] leading-[1.5] text-muted">
                Timestamps from the event, not the fetch · demo environment
              </span>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
