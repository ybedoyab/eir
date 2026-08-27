"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Timeline } from "@/components/ui/Timeline";
import { formatWhen } from "@/lib/format";
import { appointmentStatus, episodeStatus, riskStatus } from "@/lib/statusLabels";
import { eventLabel } from "@/lib/eventLabels";
import {
  getPatient,
  listAppointments,
  listPatientMedications,
  listRecovery,
  listRecoveryEvents,
  listReviews,
} from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { DomainEvent, HumanReview, Patient, PatientMedication, RecoveryEpisode } from "@/types";

export function PatientChart({ patientId }: { patientId: string }) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [medications, setMedications] = useState<PatientMedication[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSystem, setShowSystem] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextPatient, appointmentItems, episodeItems, reviewItems, medicationItems] =
        await Promise.all([
          getPatient(patientId),
          listAppointments(),
          listRecovery(),
          listReviews(false),
          listPatientMedications(patientId),
        ]);
      const ownAppointments = appointmentItems.filter((item) => item.patient_id === patientId);
      const ownEpisodes = episodeItems.filter((item) => item.patient_id === patientId);
      const eventLists = await Promise.all(ownEpisodes.map((item) => listRecoveryEvents(item.id)));
      setPatient(nextPatient);
      setAppointments(ownAppointments);
      setEpisodes(ownEpisodes);
      setEvents(eventLists.flat());
      setReviews(
        reviewItems.filter((review) => ownEpisodes.some((item) => item.id === review.episode_id)),
      );
      setMedications(medicationItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load patient");
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const nextAppointment = useMemo(
    () =>
      appointments
        .filter((item) => item.status !== "cancelled" && new Date(item.end).getTime() >= Date.now())
        .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())[0],
    [appointments],
  );
  const activeRecovery = episodes.find((item) => !["COMPLETED", "CANCELLED"].includes(item.status));
  const latestCheckin = useMemo(
    () =>
      [...events]
        .filter((item) => item.event_type === "PatientResponded")
        .sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())[0],
    [events],
  );
  const latestAdherence = useMemo(
    () =>
      [...events]
        .filter((item) => item.event_type === "AdherenceConcernDetected")
        .sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())[0],
    [events],
  );
  const timeline = useMemo(() => {
    const items = [
      ...appointments.map((item) => ({
        id: item.id,
        title: `${item.specialty} appointment`,
        detail: item.practitioner_name,
        at: formatWhen(item.start),
        ts: new Date(item.start).getTime(),
      })),
      ...events
        .filter((item) =>
          [
            "PatientResponded",
            "AdherenceConcernDetected",
            "RiskEscalated",
            "HumanReviewRequested",
            "ClinicianResolved",
          ].includes(item.event_type),
        )
        .map((item) => ({
          id: item.event_id,
          title: eventLabel(item.event_type).title,
          at: formatWhen(item.occurred_at),
          ts: new Date(item.occurred_at).getTime(),
        })),
      ...reviews.map((item) => ({
        id: item.id,
        title: item.status === "resolved" ? "Review resolved" : "Review opened",
        detail: item.reason,
        at: formatWhen(item.created_at),
        ts: new Date(item.created_at).getTime(),
      })),
    ];
    return items.sort((a, b) => b.ts - a.ts).slice(0, 8);
  }, [appointments, events, reviews]);

  if (loading) {
    return <CardSkeleton rows={8} />;
  }
  if (error) {
    return <ErrorAlert message={error} onRetry={() => void refresh()} />;
  }
  if (!patient) {
    return <EmptyState title="Patient not found" />;
  }

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Patient chart"
        title={patient.name}
        description={
          nextAppointment
            ? `Next visit ${formatWhen(nextAppointment.start)}`
            : "No upcoming appointment"
        }
        density="staff"
        actions={<Avatar name={patient.name} size="xl" />}
      />

      <div className="grid gap-7 lg:grid-cols-2">
        <section className="flex flex-col">
          <SectionHeader
            level="major"
            title="Appointments"
            meta={`${appointments.length} on file`}
          />
          {appointments.length ? (
            <div className="flex flex-col">
              {appointments.slice(0, 5).map((appointment) => (
                <div
                  key={appointment.id}
                  className="grid min-h-[60px] grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-rule"
                >
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate text-[0.9375rem] text-ink">{appointment.specialty}</span>
                    <span className="truncate font-mono text-[11.5px] text-muted">
                      {formatWhen(appointment.start)}
                    </span>
                  </span>
                  <StatusBadge status={appointmentStatus(appointment.status)} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No appointments" />
          )}
        </section>

        <section className="flex flex-col">
          <SectionHeader level="major" title="Active recovery" />
          {activeRecovery ? (
            <div className="flex flex-col gap-4 pb-2">
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={episodeStatus(activeRecovery.status)} />
                <StatusBadge status={riskStatus(activeRecovery.risk_level)} />
              </div>
              <dl className="grid grid-cols-[132px_minmax(0,1fr)] gap-x-5 gap-y-2 font-mono text-[12.5px]">
                <dt className="text-muted">next check-in</dt>
                <dd className="text-body">
                  {activeRecovery.next_follow_up_at
                    ? formatWhen(activeRecovery.next_follow_up_at)
                    : "unscheduled"}
                </dd>
                <dt className="text-muted">started</dt>
                <dd className="text-body">{formatWhen(activeRecovery.started_at)}</dd>
                <dt className="text-muted">assigned</dt>
                <dd className="text-body">
                  {activeRecovery.assigned_agents.join(", ") || "none"}
                </dd>
              </dl>
            </div>
          ) : (
            <EmptyState
              title="No active recovery"
              description="Nothing is being monitored for this patient right now."
            />
          )}
        </section>
      </div>

      <section className="mt-7 flex flex-col">
        <SectionHeader
          level="major"
          title="Medications and adherence"
          description="The latest check-in reports whether prescribed medications were taken. Drug names are matched on the server after the call — the voice check-in asks about medications in general."
        />
        <dl className="mb-5 grid gap-x-5 gap-y-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <dt className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
              Last reported adherence
            </dt>
            <dd className="text-[0.875rem] text-body">
              {String(latestCheckin?.payload.medication_adherence ?? "not yet recorded")}
            </dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
              Adherence concern
            </dt>
            <dd className="text-[0.875rem] text-body">
              {latestAdherence ? formatWhen(latestAdherence.occurred_at) : "none recorded"}
            </dd>
          </div>
        </dl>
        {medications.length ? (
          <ul className="flex flex-col">
            {medications.map((medication) => (
              <li
                key={`${medication.sku || medication.rxnorm_code || medication.name}`}
                className="grid min-h-[60px] grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-rule"
              >
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="truncate text-[0.9375rem] text-ink">{medication.name}</span>
                  <span className="truncate font-mono text-[11.5px] text-muted">
                    {[medication.dose, medication.sku].filter(Boolean).join(" · ") || "no dose recorded"}
                  </span>
                </span>
                {medication.critical ? (
                  <StatusBadge status={{ label: "Critical", tone: "danger" }} />
                ) : (
                  <span className="font-mono text-[11.5px] text-inactive">routine</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No prescribed medications" />
        )}
      </section>

      <section className="mt-7 flex flex-col">
        <SectionHeader level="major" title="Timeline" meta="most recent first" />
        {timeline.length ? <Timeline items={timeline} /> : <EmptyState title="No timeline yet" />}
      </section>

      <div className="mt-6 flex flex-col gap-3">
        <button
          type="button"
          className="focus-ink -mx-2 inline-flex min-h-11 w-fit items-center px-2 font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted hover:text-ink"
          onClick={() => setShowSystem((value) => !value)}
        >
          {showSystem ? "Hide system details" : "System details"}
        </button>
        {showSystem ? (
          <dl className="grid grid-cols-[132px_minmax(0,1fr)] gap-x-5 gap-y-2 border-t border-rule pt-4 font-mono text-[0.75rem]">
            <dt className="text-muted">patient_id</dt>
            <dd className="truncate text-body">{patient.id}</dd>
            <dt className="text-muted">date_of_birth</dt>
            <dd className="text-body">{patient.date_of_birth}</dd>
            <dt className="text-muted">episodes</dt>
            <dd className="text-body">{episodes.length}</dd>
          </dl>
        ) : null}
      </div>
    </section>
  );
}
