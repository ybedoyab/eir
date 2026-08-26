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
import { listPatientMedications, listRecovery, listRecoveryEvents } from "@/services/api";
import type { DomainEvent, PatientMedication, RecoveryEpisode } from "@/types";

const PATIENT_SAFE_EVENTS = new Set([
  "RecoveryEpisodeStarted",
  "PatientResponded",
  "FollowUpDue",
  "AppointmentRequested",
  "RecoveryEpisodeCompleted",
]);

export default function PatientRecoveryPage() {
  const session = loadSession();
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [eventsById, setEventsById] = useState<Record<string, DomainEvent[]>>({});
  const [medications, setMedications] = useState<PatientMedication[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = (await listRecovery()).filter(
        (item) => item.patient_id === session?.patient_id,
      );
      setEpisodes(items);
      const [entries, medicationItems] = await Promise.all([
        Promise.all(items.map(async (item) => [item.id, await listRecoveryEvents(item.id)] as const)),
        session?.patient_id ? listPatientMedications(session.patient_id) : Promise.resolve([]),
      ]);
      setEventsById(Object.fromEntries(entries));
      setMedications(medicationItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load recovery");
    } finally {
      setLoading(false);
    }
  }, [session?.patient_id]);

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
          <RecoverySection episode={active} events={eventsById[active.id] ?? []} />
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
          <SectionHeader title="Earlier recoveries" />
          {history.map((episode) => (
            <div
              key={episode.id}
              className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-5 border-b border-rule py-[18px]"
            >
              <div className="flex flex-col gap-1">
                <span className="text-[16px] text-body">Previous recovery</span>
                <span className="font-mono text-[12px] text-muted">
                  episode {episode.id.slice(0, 8)}
                </span>
              </div>
              <StatusBadge status={episodeStatus(episode.status)} />
              <Link
                href={`/recovery/${episode.id}`}
                className="focus-ink inline-flex min-h-11 items-center gap-2 px-2 text-[14px] text-accent hover:text-ink"
              >
                Details
                <Icon name="chevronRight" size={14} />
              </Link>
            </div>
          ))}
        </section>
      ) : null}

      <section className="on-raised flex flex-col gap-4 border-l-[3px] border-rule-strong bg-raised px-8 py-7 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-[52ch] text-[15px] leading-relaxed text-secondary">
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
}: {
  episode: RecoveryEpisode;
  events: DomainEvent[];
}) {
  const started = events.find((item) => item.event_type === "RecoveryEpisodeStarted");
  const checkin = [...events].reverse().find((item) => item.event_type === "PatientResponded");
  const context = String(started?.payload.context ?? "Recovery follow-up");
  const tasks = Array.isArray(started?.payload.tasks) ? (started?.payload.tasks as string[]) : [];
  const safeEvents = events.filter((item) => PATIENT_SAFE_EVENTS.has(item.event_type));

  return (
    <section className="flex flex-col gap-10">
      <div className="flex flex-wrap items-start justify-between gap-5 border-b border-rule-strong pb-5">
        <h2 className="font-serif text-[27px] font-medium leading-tight text-ink">{context}</h2>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={episodeStatus(episode.status)} />
          <StatusBadge status={riskStatus(episode.risk_level, "patient")} />
        </div>
      </div>

      <dl className="grid gap-0 sm:grid-cols-2">
        <div className="flex min-h-14 flex-col justify-center gap-1 border-b border-rule py-4 sm:pr-8">
          <dt className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            Last check-in
          </dt>
          <dd className="text-[17px] text-body">
            {checkin ? formatWhen(checkin.occurred_at) : "Not yet recorded"}
          </dd>
        </div>
        <div className="flex min-h-14 flex-col justify-center gap-1 border-b border-rule py-4 sm:border-l sm:border-l-rule sm:pl-8">
          <dt className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            Next check-in
          </dt>
          <dd className="text-[17px] text-body">
            {episode.next_follow_up_at ? formatWhen(episode.next_follow_up_at) : "To be scheduled"}
          </dd>
        </div>
      </dl>

      {tasks.length ? (
        <div className="flex flex-col">
          <SectionHeader title="Care tasks" />
          <ul className="flex flex-col">
            {tasks.map((task) => (
              <li
                key={task}
                className="flex min-h-14 items-center gap-3 border-b border-rule py-3 text-[17px] text-body"
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
        className="focus-ink inline-flex min-h-14 w-fit items-center gap-2.5 border border-rule-strong px-6 text-[15px] font-medium text-body hover:bg-hover"
      >
        View recovery details
        <Icon name="arrowRight" size={16} className="text-accent" />
      </Link>
    </section>
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
      <SectionHeader title="Your medications" />
      <p className="max-w-[62ch] text-[15px] leading-[1.65] text-secondary">
        Your care team asked whether you have been taking your prescribed medications. Individual
        drug names are matched after the check-in, not spoken during the call.
      </p>
      <p className="mt-4 text-[17px] text-body">
        Latest adherence: <span className="font-medium text-ink">{adherence}</span>
      </p>
      {medications.length ? (
        <ul className="mt-6 flex flex-col">
          {medications.map((medication) => (
            <li
              key={medication.sku || medication.rxnorm_code || medication.name}
              className="grid min-h-14 grid-cols-[minmax(0,1fr)_auto] items-center gap-5 border-b border-rule py-3"
            >
              <span className="text-[17px] text-body">{medication.name}</span>
              <span className="font-mono text-[13px] text-secondary">{medication.dose || "—"}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-[15px] text-muted">No prescribed medications on file.</p>
      )}
    </section>
  );
}
