"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/cn";
import { formatWait } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import {
  getRuntimeStatus,
  listPatients,
  listRecovery,
  listReviews,
  resolveReview,
} from "@/services/api";
import type { HumanReview, Patient, RecoveryEpisode, RuntimeStatus } from "@/types";

export default function ClinicianReviewsPage() {
  const { toast } = useToast();
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reviewItems, episodeItems, patientItems] = await Promise.all([
        listReviews(true),
        listRecovery(),
        listPatients(),
      ]);
      setReviews(reviewItems);
      setEpisodes(episodeItems);
      setPatients(patientItems);
      setSelectedId((current) =>
        current && reviewItems.some((item) => item.id === current)
          ? current
          : (reviewItems[0]?.id ?? null),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load reviews");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Adapter honesty: degradation changes what the clinician is being asked to do.
  useEffect(() => {
    getRuntimeStatus()
      .then(setRuntime)
      .catch(() => setRuntime(null));
  }, []);

  const names = useMemo(
    () => Object.fromEntries(patients.map((item) => [item.id, item.name])),
    [patients],
  );

  const selected = reviews.find((item) => item.id === selectedId) ?? null;
  const guardDegraded =
    runtime !== null && runtime.content_guard.managed_model_armor_available === false;

  async function resolve(id: string) {
    if (busyId) return;
    setBusyId(id);
    try {
      await resolveReview(id, "Clinician reviewed in demo workspace.");
      toast("Review resolved — the workflow resumes from the parked event");
      await refresh();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not resolve review", "error");
    } finally {
      setBusyId(null);
    }
  }

  function onListKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const index = reviews.findIndex((item) => item.id === selectedId);
    const next = event.key === "ArrowDown" ? index + 1 : index - 1;
    const target = reviews[Math.min(Math.max(next, 0), reviews.length - 1)];
    if (!target) return;
    setSelectedId(target.id);
    listRef.current
      ?.querySelector<HTMLButtonElement>(`[data-review-id="${target.id}"]`)
      ?.focus();
  }

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="font-serif text-[1.875rem] font-medium leading-[1.2] tracking-[-0.015em] text-ink">
            Reviews
          </h1>
          <p className="mt-2 text-[14.5px] leading-[1.55] text-secondary">
            {reviews.length
              ? `${reviews.length} ${reviews.length === 1 ? "workflow is" : "workflows are"} parked and waiting on you. Nothing downstream runs until you answer.`
              : "Nothing is parked. The runtime is running every cascade to completion."}
          </p>
        </div>
        <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
          Pending {reviews.length}
        </span>
      </header>

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <CardSkeleton rows={4} />
      ) : reviews.length ? (
        <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_400px]">
          {/* worklist */}
          <div className="flex min-w-0 flex-col">
            <div className="hidden grid-cols-[minmax(0,1fr)_108px_168px_92px] gap-5 border-b border-rule-strong pb-2.5 md:grid">
              {["Patient", "Risk", "Asked for", "Waiting"].map((column, index) => (
                <span
                  key={column}
                  className={cn(
                    "font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted",
                    index === 3 && "text-right",
                  )}
                >
                  {column}
                </span>
              ))}
            </div>

            <div ref={listRef} onKeyDown={onListKeyDown}>
              {reviews.map((review) => {
                const episode = episodes.find((item) => item.id === review.episode_id);
                const patientName = episode ? (names[episode.patient_id] ?? "Patient") : "Patient";
                const active = review.id === selectedId;
                return (
                  <button
                    key={review.id}
                    type="button"
                    data-review-id={review.id}
                    aria-current={active ? "true" : undefined}
                    onClick={() => setSelectedId(review.id)}
                    className={cn(
                      "focus-ink grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-5 gap-y-2 border-b border-rule border-l-[3px] py-3 pr-1 text-left md:grid-cols-[minmax(0,1fr)_108px_168px_92px]",
                      active
                        ? "on-raised border-l-accent bg-raised pl-[13px]"
                        : "border-l-transparent pl-4 hover:bg-hover",
                    )}
                    style={{ minHeight: 60 }}
                  >
                    <span className="flex min-w-0 flex-col gap-[3px]">
                      <span className="truncate text-[15.5px] font-medium text-ink">
                        {patientName}
                      </span>
                      <span className="truncate font-mono text-[11.5px] text-muted">
                        episode {review.episode_id.slice(0, 8)} · {review.agent_name}
                      </span>
                    </span>
                    {episode ? (
                      <StatusBadge status={riskStatus(episode.risk_level)} className="h-6" />
                    ) : (
                      <span className="font-mono text-[0.75rem] text-muted">—</span>
                    )}
                    <span className="col-span-2 truncate font-mono text-[12.5px] text-body md:col-span-1">
                      {review.pending_capability ?? review.capability}
                    </span>
                    <span
                      className={cn(
                        "col-start-2 row-start-1 text-right font-mono text-[12.5px] md:col-start-auto md:row-start-auto",
                        episode?.risk_level === "HIGH" || episode?.risk_level === "CRITICAL"
                          ? "text-high"
                          : "text-secondary",
                      )}
                    >
                      {formatWait(review.created_at).replace(" waiting", "")}
                    </span>
                  </button>
                );
              })}
            </div>

            {guardDegraded ? (
              <div className="on-raised mt-6 flex items-center gap-3 border-l-[3px] border-warn bg-raised px-4 py-3">
                <span className="font-mono text-[0.75rem] font-medium uppercase tracking-[0.08em] text-warn">
                  Degraded
                </span>
                <span className="text-[13.5px] leading-snug text-secondary">
                  Managed content screening is unavailable, so sensitive writes are routed to you
                  rather than auto-approved.
                </span>
              </div>
            ) : null}

            <div className="mt-6 flex flex-wrap items-center justify-between gap-5 border-t border-rule pt-4">
              <span className="font-mono text-[0.75rem] text-muted">↑↓ move between reviews</span>
              <span className="font-mono text-[0.75rem] text-muted">
                Demo environment · no real patient data
              </span>
            </div>
          </div>

          {/* why you are being asked — not a span tree */}
          {selected ? (
            <ReviewDetail
              review={selected}
              episode={episodes.find((item) => item.id === selected.episode_id)}
              patientName={
                names[
                  episodes.find((item) => item.id === selected.episode_id)?.patient_id ?? ""
                ] ?? "this patient"
              }
              busy={busyId === selected.id}
              onResolve={() => void resolve(selected.id)}
            />
          ) : null}
        </div>
      ) : (
        <EmptyState
          title="You're all caught up"
          description="No pending clinician reviews. Every cascade is running to completion."
        />
      )}
    </>
  );
}

function ReviewDetail({
  review,
  episode,
  patientName,
  busy,
  onResolve,
}: {
  review: HumanReview;
  episode?: RecoveryEpisode;
  patientName: string;
  busy: boolean;
  onResolve: () => void;
}) {
  const capability = review.pending_capability ?? review.capability;
  return (
    <aside className="on-raised flex flex-col border-l border-rule bg-raised lg:sticky lg:top-6">
      <div className="flex flex-col gap-3 border-b border-rule px-7 py-6">
        {episode ? <StatusBadge status={riskStatus(episode.risk_level)} /> : null}
        <h2 className="font-serif text-[1.5625rem] font-medium leading-[1.25] text-ink">
          Resolve {capability} for {patientName}?
        </h2>
        <p className="text-[14.5px] leading-[1.6] text-secondary">
          The {review.agent_name} agent stopped here and took no clinical action.
        </p>
      </div>

      <div className="flex flex-col gap-2.5 border-b border-rule px-7 py-5">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
          Why it stopped
        </span>
        <blockquote className="m-0 border-l-2 border-rule-strong pl-3.5 font-serif text-[1.0625rem] leading-[1.55] text-ink">
          {review.reason}
        </blockquote>
      </div>

      <dl className="grid grid-cols-[96px_minmax(0,1fr)] gap-x-4 gap-y-2 border-b border-rule px-7 py-5 text-[13.5px] leading-snug">
        <dt className="text-muted">Episode</dt>
        <dd className="font-mono text-[12.5px] text-body">{review.episode_id.slice(0, 8)}</dd>
        <dt className="text-muted">Agent</dt>
        <dd className="text-body">{review.agent_name}</dd>
        <dt className="text-muted">Capability</dt>
        <dd className="font-mono text-[12.5px] text-body">{capability}</dd>
        <dt className="text-muted">Rule</dt>
        <dd className="text-body">Blocking capability — always parked for a human</dd>
        {episode ? (
          <>
            <dt className="text-muted">Episode state</dt>
            <dd>
              <StatusBadge status={episodeStatus(episode.status)} className="h-6" />
            </dd>
          </>
        ) : null}
      </dl>

      <div className="flex flex-col gap-2 px-7 py-5">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
          If you resolve
        </span>
        <p className="text-[13.5px] leading-[1.6] text-secondary">
          The parked event is reconstructed and replayed with an approval stamp, and the workflow
          continues from exactly where it halted.
        </p>
      </div>

      <div className="mt-auto flex flex-col gap-2.5 border-t border-rule-strong px-7 pb-6 pt-5">
        <Button className="min-h-12 w-full" disabled={busy} onClick={onResolve}>
          <Icon name="approve" size={17} />
          {busy ? "Resolving…" : "Resolve and resume"}
        </Button>
        <Link
          href="/observability"
          className="focus-ink inline-flex min-h-11 items-center gap-2 font-mono text-[11.5px] text-accent hover:text-ink"
        >
          Open full trace in operations
          <Icon name="open" size={14} />
        </Link>
      </div>
    </aside>
  );
}
