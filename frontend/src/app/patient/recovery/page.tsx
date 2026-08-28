"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Timeline } from "@/components/ui/Timeline";
import { loadSession } from "@/lib/auth";
import { formatWhen } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import { eventLabel } from "@/lib/eventLabels";
import {
  listPatientMedications,
  listRecovery,
  listRecoveryEvents,
  recoveryVideoUrl,
  requestRecoveryVideo,
} from "@/services/api";
import type { DomainEvent, PatientMedication, RecoveryEpisode } from "@/types";

const PATIENT_SAFE_EVENTS = new Set([
  "RecoveryEpisodeStarted",
  "PatientResponded",
  "FollowUpDue",
  "AppointmentRequested",
  "RecoveryEpisodeCompleted",
  "RecoveryVideoReady",
  "RecoveryVideoFailed",
]);

export default function PatientRecoveryPage() {
  // Read once per mount; `loadSession` hits localStorage + JSON.parse, and these
  // pages re-render on every fetch/state tick.
  const [session] = useState(loadSession);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [eventsById, setEventsById] = useState<Record<string, DomainEvent[]>>({});
  const [medications, setMedications] = useState<PatientMedication[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // `silent` refetches without re-entering the skeleton state. Actions on the page (asking for
  // a new recovery video) need their data refreshed, but flipping `loading` back on unmounts
  // the whole section — which restarts any playing clip and reads as a full page reload.
  const refresh = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!options?.silent) setLoading(true);
      setError(null);
      try {
        const items = (await listRecovery()).filter(
          (item) => item.patient_id === session?.patient_id,
        );
        setEpisodes(items);
        const [entries, medicationItems] = await Promise.all([
          Promise.all(
            items.map(async (item) => [item.id, await listRecoveryEvents(item.id)] as const),
          ),
          session?.patient_id ? listPatientMedications(session.patient_id) : Promise.resolve([]),
        ]);
        setEventsById(Object.fromEntries(entries));
        setMedications(medicationItems);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load recovery");
      } finally {
        setLoading(false);
      }
    },
    [session?.patient_id],
  );

  const refreshQuietly = useCallback(() => void refresh({ silent: true }), [refresh]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const active = episodes.find((item) => !["COMPLETED", "CANCELLED"].includes(item.status));
  const history = episodes.filter((item) => item !== active);

  return (
    <>
      <PageHeader
        density="patient"
        title="Recovery follow-up"
        description="Check-ins, care tasks, and the next time your care team will look in."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <CardSkeleton rows={6} />
      ) : active ? (
        <>
          <RecoverySection
            episode={active}
            events={eventsById[active.id] ?? []}
            onRefresh={refreshQuietly}
          />
          <MedicationsSection medications={medications} events={eventsById[active.id] ?? []} />
        </>
      ) : (
        <EmptyState
          title="No active recovery"
          description="If you recently had a procedure, recovery follow-up will appear here."
        />
      )}

      {history.length ? (
        <section className="flex flex-col">
          <SectionHeader
            level="major"
            title="Earlier recoveries"
            meta={`${history.length} on record`}
          />
          {history.map((episode) => (
            <div
              key={episode.id}
              className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-5 border-b border-rule py-[18px]"
            >
              <div className="flex flex-col gap-1">
                <span className="text-[1rem] text-body">Previous recovery</span>
                <span className="font-mono text-[0.75rem] text-muted">
                  episode {episode.id.slice(0, 8)}
                </span>
              </div>
              <StatusBadge status={episodeStatus(episode.status)} />
              <Link
                href={`/recovery/${episode.id}`}
                className="focus-ink inline-flex min-h-11 items-center gap-2 px-2 text-[0.875rem] text-accent hover:text-ink"
              >
                Details
                <Icon name="chevronRight" size={14} />
              </Link>
            </div>
          ))}
        </section>
      ) : null}

      <section className="on-raised flex flex-col gap-4 border-l-[3px] border-accent bg-raised px-8 py-7 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-[52ch] text-[0.9375rem] leading-relaxed text-secondary">
          The full autonomous recovery story — every event, gate and halt — can be walked through
          in the guided demo.
        </p>
        <Link href="/demo" className="shrink-0">
          <Button variant="secondary">
            Open guided demo
            <Icon name="arrowRight" size={16} />
          </Button>
        </Link>
      </section>
    </>
  );
}

function RecoverySection({
  episode,
  events,
  onRefresh,
}: {
  episode: RecoveryEpisode;
  events: DomainEvent[];
  onRefresh: () => void;
}) {
  const started = events.find((item) => item.event_type === "RecoveryEpisodeStarted");
  const checkin = [...events].reverse().find((item) => item.event_type === "PatientResponded");
  const context = String(started?.payload.context ?? "Recovery follow-up");
  const tasks = Array.isArray(started?.payload.tasks) ? (started?.payload.tasks as string[]) : [];
  const safeEvents = events.filter((item) => PATIENT_SAFE_EVENTS.has(item.event_type));

  return (
    <section className="flex flex-col">
      <SectionHeader
        level="major"
        title="Current recovery"
        meta={`episode ${episode.id.slice(0, 8)}`}
      />

      {/* Blocks inside the section sit at gap-8 — half the gap-14 that
          separates one major section from the next. */}
      <div className="flex flex-col gap-8">
        {/* Episode identity and its two dates are one accent-tinted panel: this
            is the answer the page exists to give, so it is the one block that
            is a surface rather than ruled rows. */}
        <div className="on-tint flex flex-col bg-accent-tint">
          <div className="flex flex-wrap items-start justify-between gap-x-5 gap-y-3 px-6 pb-5 pt-6">
            <h3 className="font-serif text-[1.6875rem] font-medium leading-tight text-ink">
              {context}
            </h3>
            <div className="flex flex-wrap gap-2">
              <StatusBadge status={episodeStatus(episode.status)} />
              <StatusBadge status={riskStatus(episode.risk_level, "patient")} />
            </div>
          </div>

          <dl className="grid border-t border-rule-strong sm:grid-cols-2">
            <div className="flex min-h-14 flex-col justify-center gap-1 px-6 py-5">
              <dt className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-accent">
                Last check-in
              </dt>
              <dd className="text-[1.0625rem] text-body">
                {checkin ? formatWhen(checkin.occurred_at) : "Not yet recorded"}
              </dd>
            </div>
            <div className="flex min-h-14 flex-col justify-center gap-1 border-t border-rule-strong px-6 py-5 sm:border-l sm:border-t-0 sm:border-l-rule-strong">
              <dt className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-accent">
                Next check-in
              </dt>
              <dd className="text-[1.0625rem] text-body">
                {episode.next_follow_up_at
                  ? formatWhen(episode.next_follow_up_at)
                  : "To be scheduled"}
              </dd>
            </div>
          </dl>
        </div>

        <RecoveryVideoPanel episodeId={episode.id} events={events} onRefresh={onRefresh} />

        {tasks.length ? (
          <div className="flex flex-col">
            <SectionHeader title="Care tasks" />
            <ul className="flex flex-col">
              {tasks.map((task) => (
                <li
                  key={task}
                  className="flex min-h-14 items-center gap-3 border-b border-rule py-3 text-[1.0625rem] text-body"
                >
                  {task}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {safeEvents.length ? (
          <div className="flex flex-col">
            <SectionHeader title="Recent updates" />
            <Timeline
              items={safeEvents
                .slice(-5)
                .reverse()
                .map((event) => ({
                  id: event.event_id,
                  title: eventLabel(event.event_type).title,
                  at: formatWhen(event.occurred_at),
                }))}
            />
          </div>
        ) : null}

        <Link
          href={`/recovery/${episode.id}`}
          className="focus-ink inline-flex min-h-14 w-fit items-center gap-2.5 border border-accent px-6 text-[0.9375rem] font-medium text-accent hover:bg-accent-tint"
        >
          View recovery details
          <Icon name="arrowRight" size={16} />
        </Link>
      </div>
    </section>
  );
}

function RecoveryVideoPanel({
  episodeId,
  events,
  onRefresh,
}: {
  episodeId: string;
  events: DomainEvent[];
  onRefresh: () => void;
}) {
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const latestVideoEvent = [...events]
    .reverse()
    .find((item) =>
      ["RecoveryVideoReady", "RecoveryVideoRequested", "RecoveryVideoFailed"].includes(
        item.event_type,
      ),
    );
  const pending = latestVideoEvent?.event_type === "RecoveryVideoRequested" || requesting;
  const videoUrl =
    latestVideoEvent?.event_type === "RecoveryVideoReady"
      ? String(latestVideoEvent.payload.video_url ?? "")
      : "";
  const failureReason =
    latestVideoEvent?.event_type === "RecoveryVideoFailed"
      ? String(latestVideoEvent.payload.reason ?? "unknown error")
      : "";

  const handleRegenerate = async () => {
    setRequesting(true);
    setError(null);
    try {
      // Only an explicit regeneration forces a fresh Veo call; the first request is happy to
      // reuse a cached clip for the same instructions.
      await requestRecoveryVideo(episodeId, Boolean(videoUrl));
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request a new video");
    } finally {
      setRequesting(false);
    }
  };

  return (
    <div className="flex flex-col">
      {/* The button lives in the header so the header's rule spans the block
          instead of being squeezed to a stub beside it. */}
      <SectionHeader
        title="Recovery video"
        action={
          <Button variant="secondary" onClick={() => void handleRegenerate()} disabled={pending}>
            {pending ? "Generating…" : videoUrl ? "Regenerate video" : "Generate video"}
          </Button>
        }
      />
      {error ? <ErrorAlert message={error} onRetry={() => void handleRegenerate()} /> : null}
      {videoUrl ? (
        <div className="flex justify-center">
          <video
            key={videoUrl}
            src={recoveryVideoUrl(videoUrl)}
            controls
            playsInline
            className="aspect-[9/16] w-full max-w-[360px] border border-rule-strong bg-raised"
          />
        </div>
      ) : pending ? (
        <p className="text-[0.9375rem] text-muted">
          Your personalized recovery video is being generated — this can take up to a minute.
        </p>
      ) : failureReason ? (
        <p className="text-[0.9375rem] text-muted">
          Video generation didn&apos;t complete ({failureReason}). Text instructions below
          remain the source of truth.
        </p>
      ) : (
        <p className="text-[0.9375rem] text-muted">
          No recovery video yet. Text instructions below remain the source of truth.
        </p>
      )}
    </div>
  );
}

function MedicationsSection({
  medications,
  events,
}: {
  medications: PatientMedication[];
  events: DomainEvent[];
}) {
  const checkin = [...events].reverse().find((item) => item.event_type === "PatientResponded");
  const adherence = String(checkin?.payload.medication_adherence ?? "Not yet recorded");

  return (
    <section className="flex flex-col">
      <SectionHeader
        level="major"
        title="Your medications"
        description="Your care team asked whether you have been taking your prescribed medications. Individual drug names are matched after the check-in, not spoken during the call."
        meta={medications.length ? `${medications.length} on file` : undefined}
      />
      <p className="text-[1.0625rem] text-body">
        Latest adherence: <span className="font-medium text-ink">{adherence}</span>
      </p>
      {medications.length ? (
        <ul className="mt-6 flex flex-col">
          {medications.map((medication) => (
            <li
              key={medication.sku || medication.rxnorm_code || medication.name}
              className="grid min-h-14 grid-cols-[minmax(0,1fr)_auto] items-center gap-5 border-b border-rule py-3"
            >
              <span className="text-[1.0625rem] text-body">{medication.name}</span>
              <span className="font-mono text-[0.8125rem] text-secondary">{medication.dose || "—"}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-[0.9375rem] text-muted">No prescribed medications on file.</p>
      )}
    </section>
  );
}
