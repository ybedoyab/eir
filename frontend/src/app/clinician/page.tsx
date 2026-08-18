"use client";

import { AlertTriangle, CalendarDays, ClipboardCheck, HeartPulse, Users } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { loadSession } from "@/lib/auth";
import { formatWhen, greeting, shortClinicianName } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import { listAppointments, listPatients, listRecovery, listReviews } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { HumanReview, Patient, RecoveryEpisode } from "@/types";

export default function ClinicianHomePage() {
  const session = loadSession();
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [reviewItems, episodeItems, patientItems, appointmentItems] = await Promise.all([
        listReviews(true),
        listRecovery(),
        listPatients(),
        listAppointments(),
      ]);
      setReviews(reviewItems);
      setEpisodes(episodeItems);
      setPatients(patientItems);
      setAppointments(appointmentItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load clinician workspace");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const names = useMemo(
    () => Object.fromEntries(patients.map((item) => [item.id, item.name])),
    [patients],
  );
  const today = useMemo(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    return appointments
      .filter(
        (item) =>
          item.status !== "cancelled" &&
          new Date(item.start) >= start &&
          new Date(item.start) < end,
      )
      .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());
  }, [appointments]);
  const escalated = episodes.filter((item) => item.status === "ESCALATED");
  const activeRecoveries = episodes.filter(
    (item) => !["COMPLETED", "CANCELLED"].includes(item.status),
  );

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Clinician workspace"
        title={greeting(shortClinicianName(session?.display_name ?? "Doctor"))}
        description="Reviews, today’s schedule, and recovery escalations from stored synthetic data."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <CardSkeleton rows={2} />
          <CardSkeleton rows={2} />
          <CardSkeleton rows={2} />
          <CardSkeleton rows={2} />
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Reviews waiting" value={reviews.length} icon={ClipboardCheck} />
            <StatCard label="Escalated recoveries" value={escalated.length} icon={AlertTriangle} />
            <StatCard label="Today’s appointments" value={today.length} icon={CalendarDays} />
            <StatCard
              label="Patients in active recovery"
              value={activeRecoveries.length}
              icon={HeartPulse}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">Needs attention</h2>
                <Link href="/clinician/reviews" className="text-sm font-medium text-teal-700">
                  View all
                </Link>
              </div>
              <div className="space-y-3">
                {reviews.slice(0, 5).map((review) => {
                  const episode = episodes.find((item) => item.id === review.episode_id);
                  const patientName = episode ? names[episode.patient_id] : "Patient";
                  return (
                    <div key={review.id} className="rounded-xl border border-slate-200 p-4">
                      <div className="flex items-start gap-3">
                        <Avatar name={patientName ?? "Patient"} size="sm" />
                        <div>
                          <p className="text-sm font-medium text-slate-900">{patientName}</p>
                          <p className="mt-1 text-sm text-slate-600">{review.reason}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
                {!reviews.length ? (
                  <EmptyState title="You're all caught up" icon={ClipboardCheck} />
                ) : null}
              </div>
            </Card>

            <Card>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">Today’s schedule</h2>
                <Link href="/clinician/schedule" className="text-sm font-medium text-teal-700">
                  View all
                </Link>
              </div>
              <div className="space-y-3">
                {today.slice(0, 5).map((appointment) => (
                  <Link
                    key={appointment.id}
                    href={`/clinician/patients/${appointment.patient_id}`}
                    className="block rounded-xl border border-slate-200 p-4 hover:border-teal-200 hover:bg-teal-50/40"
                  >
                    <p className="text-sm font-medium text-slate-900">
                      {names[appointment.patient_id] ?? "Patient"}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      {formatWhen(appointment.start)} · {appointment.specialty}
                    </p>
                  </Link>
                ))}
                {!today.length ? (
                  <EmptyState title="No appointments today" icon={CalendarDays} />
                ) : null}
              </div>
            </Card>
          </div>

          <Card>
            <h2 className="mb-4 text-base font-semibold text-slate-900">Recovery escalations</h2>
            <div className="space-y-3">
              {escalated.slice(0, 5).map((episode) => (
                <div
                  key={episode.id}
                  className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-center gap-3">
                    <Avatar name={names[episode.patient_id] ?? "Patient"} />
                    <div>
                      <p className="font-medium text-slate-900">
                        {names[episode.patient_id] ?? "Patient"}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <StatusBadge status={episodeStatus(episode.status)} />
                        <StatusBadge status={riskStatus(episode.risk_level)} />
                      </div>
                    </div>
                  </div>
                  <Link href={`/clinician/patients/${episode.patient_id}`}>
                    <Button variant="secondary">Open chart</Button>
                  </Link>
                </div>
              ))}
              {!escalated.length ? (
                <EmptyState title="No escalated recoveries" icon={HeartPulse} />
              ) : null}
            </div>
          </Card>

          <Card>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">Recent patients</h2>
              <Link href="/clinician/patients" className="text-sm font-medium text-teal-700">
                View all
              </Link>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {patients.slice(0, 6).map((patient) => (
                <Link
                  key={patient.id}
                  href={`/clinician/patients/${patient.id}`}
                  className="flex items-center gap-3 rounded-xl border border-slate-200 p-4 transition hover:border-teal-200 hover:bg-teal-50/40"
                >
                  <Avatar name={patient.name} />
                  <span className="font-medium text-slate-900">{patient.name}</span>
                </Link>
              ))}
            </div>
            {!patients.length ? <EmptyState title="No patients" icon={Users} /> : null}
          </Card>
        </>
      )}
    </section>
  );
}
