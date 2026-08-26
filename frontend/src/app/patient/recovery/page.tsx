"use client";

import { CheckCircle2, HeartPulse, Pill } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
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
    <section className="space-y-6">
      <PageHeader
        eyebrow="Recovery"
        title="Recovery follow-up"
        description="Check-ins, care tasks, and the next time your care team will look in."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      {loading ? (
        <CardSkeleton rows={6} />
      ) : active ? (
        <>
          <RecoveryCard episode={active} events={eventsById[active.id] ?? []} />
          <MedicationsCard
            medications={medications}
            events={eventsById[active.id] ?? []}
          />
        </>
      ) : (
        <EmptyState
          title="No active recovery"
          description="If you recently had a procedure, recovery follow-up will appear here."
          icon={HeartPulse}
        />
      )}
      {history.map((episode) => (
        <Card key={episode.id}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-medium text-slate-900">Previous recovery</p>
              <div className="mt-2">
                <StatusBadge status={episodeStatus(episode.status)} />
              </div>
            </div>
            <Link href={`/recovery/${episode.id}`} className="text-sm font-medium text-teal-700">
              View recovery details
            </Link>
          </div>
        </Card>
      ))}
      <Card>
        <p className="text-sm text-slate-600">
          Judges can walk the full autonomous recovery story separately.
        </p>
        <Link href="/demo" className="mt-3 inline-block">
          <Button variant="secondary">Open guided recovery demo</Button>
        </Link>
      </Card>
    </section>
  );
}

function RecoveryCard({
  episode,
  events,
}: {
  episode: RecoveryEpisode;
  events: DomainEvent[];
}) {
  const started = events.find((item) => item.event_type === "RecoveryEpisodeStarted");
  const checkin = [...events].reverse().find((item) => item.event_type === "PatientResponded");
  const context = String(started?.payload.context ?? "Recovery follow-up");
  const tasks = Array.isArray(started?.payload.tasks)
    ? (started?.payload.tasks as string[])
    : [];
  const safeEvents = events.filter((item) => PATIENT_SAFE_EVENTS.has(item.event_type));

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-teal-700">Recovery status</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">{context}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={episodeStatus(episode.status)} />
          <StatusBadge status={riskStatus(episode.risk_level, "patient")} />
        </div>
      </div>
      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Last check-in</dt>
          <dd className="mt-1 text-sm text-slate-800">
            {checkin ? formatWhen(checkin.occurred_at) : "Not yet recorded"}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Next check-in</dt>
          <dd className="mt-1 text-sm text-slate-800">
            {episode.next_follow_up_at ? formatWhen(episode.next_follow_up_at) : "To be scheduled"}
          </dd>
        </div>
      </dl>
      {tasks.length ? (
        <div className="mt-6">
          <p className="mb-2 text-sm font-medium text-slate-800">Care tasks</p>
          <ul className="space-y-2">
            {tasks.map((task) => (
              <li key={task} className="flex items-center gap-2 text-sm text-slate-700">
                <CheckCircle2 aria-hidden className="h-4 w-4 text-teal-700" />
                {task}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {safeEvents.length ? (
        <div className="mt-6">
          <p className="mb-3 text-sm font-medium text-slate-800">Recent updates</p>
          <Timeline
            items={safeEvents.slice(-5).reverse().map((event) => ({
              id: event.event_id,
              title: eventLabel(event.event_type).title,
              at: formatWhen(event.occurred_at),
            }))}
          />
        </div>
      ) : null}
      <Link href={`/recovery/${episode.id}`} className="mt-6 inline-block">
        <Button variant="secondary">View recovery details</Button>
      </Link>
    </Card>
  );
}

function MedicationsCard({
  medications,
  events,
}: {
  medications: PatientMedication[];
  events: DomainEvent[];
}) {
  const checkin = [...events].reverse().find((item) => item.event_type === "PatientResponded");
  const adherence = String(checkin?.payload.medication_adherence ?? "Not yet recorded");

  return (
    <Card>
      <h2 className="text-base font-semibold text-slate-900">Your medications</h2>
      <p className="mt-2 text-sm text-slate-600">
        Your care team asked whether you have been taking your prescribed medications. Individual
        drug names are matched after the check-in, not spoken during the call.
      </p>
      <p className="mt-4 text-sm text-slate-800">
        Latest adherence: <span className="font-medium">{adherence}</span>
      </p>
      {medications.length ? (
        <ul className="mt-4 space-y-3">
          {medications.map((medication) => (
            <li
              key={`${medication.sku || medication.rxnorm_code || medication.name}`}
              className="flex items-start gap-3 rounded-xl border border-slate-200 p-4"
            >
              <Pill aria-hidden className="mt-0.5 h-4 w-4 text-teal-700" />
              <div>
                <p className="font-medium text-slate-900">{medication.name}</p>
                {medication.dose ? (
                  <p className="mt-1 text-sm text-slate-600">{medication.dose}</p>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-500">No prescribed medications on file.</p>
      )}
    </Card>
  );
}
