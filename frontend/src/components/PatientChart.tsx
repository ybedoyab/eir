"use client";

import {
  AlertTriangle,
  CalendarDays,
  ClipboardCheck,
  HeartPulse,
  Pill,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
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
        icon: CalendarDays,
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
          icon: item.event_type.includes("Review") ? ClipboardCheck : HeartPulse,
        })),
      ...reviews.map((item) => ({
        id: item.id,
        title: item.status === "resolved" ? "Review resolved" : "Review opened",
        detail: item.reason,
        at: formatWhen(item.created_at),
        ts: new Date(item.created_at).getTime(),
        icon: item.status === "pending" ? AlertTriangle : ClipboardCheck,
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
    <section className="space-y-6">
      <PageHeader
        eyebrow="Patient chart"
        title={patient.name}
        description={
          nextAppointment
            ? `Next visit ${formatWhen(nextAppointment.start)}`
            : "No upcoming appointment"
        }
        actions={<Avatar name={patient.name} size="xl" />}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-base font-semibold text-slate-900">Appointments</h2>
          {appointments.length ? (
            <div className="space-y-3">
              {appointments.slice(0, 5).map((appointment) => (
                <div key={appointment.id} className="rounded-xl border border-slate-200 p-4">
                  <p className="font-medium text-slate-900">{appointment.specialty}</p>
                  <p className="text-sm text-slate-600">{formatWhen(appointment.start)}</p>
                  <div className="mt-2">
                    <StatusBadge status={appointmentStatus(appointment.status)} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No appointments" />
          )}
        </Card>
        <Card>
          <h2 className="mb-4 text-base font-semibold text-slate-900">Active recovery</h2>
          {activeRecovery ? (
            <div className="space-y-3">
              <StatusBadge status={episodeStatus(activeRecovery.status)} />
              <StatusBadge status={riskStatus(activeRecovery.risk_level)} />
              <p className="text-sm text-slate-600">
                Next check-in{" "}
                {activeRecovery.next_follow_up_at
                  ? formatWhen(activeRecovery.next_follow_up_at)
                  : "unscheduled"}
              </p>
            </div>
          ) : (
            <EmptyState title="No active recovery" icon={HeartPulse} />
          )}
        </Card>
      </div>
      <Card>
        <h2 className="mb-4 text-base font-semibold text-slate-900">Medications and adherence</h2>
        <p className="mb-4 text-sm text-slate-600">
          Latest check-in reports whether prescribed medications were taken. Drug names are
          matched on the server after the call — the voice check-in asks about medications in
          general.
        </p>
        <dl className="mb-4 grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500">Last reported adherence</dt>
            <dd className="mt-1 text-sm text-slate-800">
              {String(latestCheckin?.payload.medication_adherence ?? "Not yet recorded")}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500">Adherence concern</dt>
            <dd className="mt-1 text-sm text-slate-800">
              {latestAdherence
                ? formatWhen(latestAdherence.occurred_at)
                : "None recorded"}
            </dd>
          </div>
        </dl>
        {medications.length ? (
          <ul className="space-y-3">
            {medications.map((medication) => (
              <li
                key={`${medication.sku || medication.rxnorm_code || medication.name}`}
                className="rounded-xl border border-slate-200 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Pill aria-hidden className="h-4 w-4 text-teal-700" />
                  <p className="font-medium text-slate-900">{medication.name}</p>
                  {medication.critical ? (
                    <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                      Critical
                    </span>
                  ) : null}
                </div>
                {medication.dose ? (
                  <p className="mt-1 text-sm text-slate-600">{medication.dose}</p>
                ) : null}
                {medication.sku ? (
                  <p className="mt-1 font-mono text-xs text-slate-400">{medication.sku}</p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No prescribed medications" icon={Pill} />
        )}
      </Card>
      <Card>
        <h2 className="mb-4 text-base font-semibold text-slate-900">Timeline</h2>
        {timeline.length ? <Timeline items={timeline} /> : <EmptyState title="No timeline yet" />}
      </Card>
      <button
        type="button"
        className="text-xs font-medium text-slate-400 hover:text-slate-600"
        onClick={() => setShowSystem((value) => !value)}
      >
        {showSystem ? "Hide system details" : "System details"}
      </button>
      {showSystem ? (
        <Card>
          <p className="font-mono text-xs text-slate-500">{patient.id}</p>
        </Card>
      ) : null}
    </section>
  );
}
