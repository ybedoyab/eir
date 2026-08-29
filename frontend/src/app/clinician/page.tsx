"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatCard, StatStrip } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { loadSession } from "@/lib/auth";
import { displayPatientId, formatWait, formatWhen, greeting, shortClinicianName } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import { listAppointments, listPatients, listRecovery, listReviews } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { HumanReview, Patient, RecoveryEpisode } from "@/types";

export default function ClinicianHomePage() {
  // Read once per mount; `loadSession` hits localStorage + JSON.parse, and these
  // pages re-render on every fetch/state tick.
  const [session] = useState(loadSession);
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
  const oldestWait = reviews.length
    ? formatWait(
        reviews.reduce((oldest, item) =>
          new Date(item.created_at) < new Date(oldest.created_at) ? item : oldest,
        ).created_at,
      )
    : null;

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="font-serif text-[1.875rem] font-medium leading-[1.2] tracking-[-0.015em] text-ink">
            {greeting(shortClinicianName(session?.display_name ?? "Doctor"))}.
          </h1>
          <p className="mt-2 text-[14.5px] leading-[1.55] text-secondary">
            Reviews, today’s schedule and recovery escalations, from the hospital record.
          </p>
        </div>
      </header>

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <CardSkeleton rows={4} />
      ) : (
        <>
          <StatStrip className="sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Reviews waiting"
              value={reviews.length}
              tone={reviews.length ? "high" : "ink"}
              hint={oldestWait ? `oldest ${oldestWait}` : "nothing parked on you"}
            />
            <StatCard
              label="Escalated recoveries"
              value={escalated.length}
              tone={escalated.length ? "warn" : "ink"}
              hint={`of ${activeRecoveries.length} active`}
            />
            <StatCard
              label="Today’s appointments"
              value={today.length}
              hint={
                today.length ? `next ${formatWhen(today[0].start)}` : "clinic list is clear today"
              }
            />
            <StatCard
              label="In active recovery"
              value={activeRecoveries.length}
              hint="followed up on a schedule"
            />
          </StatStrip>

          <div className="grid gap-8 lg:grid-cols-2">
            <section className="flex min-w-0 flex-col">
              <SectionHeader
                level="major"
                title="Needs attention"
                actionHref="/clinician/reviews"
                actionLabel="Open review queue"
              />
              {reviews.length ? (
                reviews.slice(0, 5).map((review) => {
                  const episode = episodes.find((item) => item.id === review.episode_id);
                  const patientName = episode
                    ? (names[episode.patient_id] ?? "Patient")
                    : "Patient";
                  return (
                    <Link
                      key={review.id}
                      href="/clinician/reviews"
                      className="focus-ink group grid min-h-[60px] grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-4 border-b border-rule py-3 pl-1 pr-1 hover:bg-hover"
                    >
                      <span className="flex min-w-0 flex-col gap-[3px]">
                        <span className="truncate text-[0.9375rem] font-medium text-ink">
                          {patientName}
                        </span>
                        <span className="truncate text-[0.8125rem] text-secondary">
                          {review.reason}
                        </span>
                      </span>
                      {episode ? (
                        <StatusBadge status={riskStatus(episode.risk_level)} className="h-6" />
                      ) : null}
                      <Icon
                        name="chevronRight"
                        size={15}
                        className="text-muted opacity-0 group-hover:opacity-100"
                      />
                    </Link>
                  );
                })
              ) : (
                <EmptyState
                  title="You're all caught up"
                  description="No workflow is parked on a clinician right now."
                />
              )}
            </section>

            <section className="flex min-w-0 flex-col">
              <SectionHeader
                level="major"
                title="Today’s schedule"
                actionHref="/clinician/schedule"
                actionLabel="Full schedule"
              />
              {today.length ? (
                today.slice(0, 5).map((appointment) => (
                  <Link
                    key={appointment.id}
                    href={`/clinician/patients/${appointment.patient_id}`}
                    className="focus-ink group grid min-h-[60px] grid-cols-[84px_minmax(0,1fr)_auto] items-center gap-4 border-b border-rule py-3 pl-1 pr-1 hover:bg-hover"
                  >
                    <span className="font-mono text-[0.8125rem] text-secondary">
                      {formatWhen(appointment.start).split(", ").pop()}
                    </span>
                    <span className="flex min-w-0 flex-col gap-[3px]">
                      <span className="truncate text-[0.9375rem] font-medium text-ink">
                        {names[appointment.patient_id] ?? "Patient"}
                      </span>
                      <span className="truncate text-[0.8125rem] text-secondary">
                        {appointment.specialty}
                      </span>
                    </span>
                    <Icon
                      name="chevronRight"
                      size={15}
                      className="text-muted opacity-0 group-hover:opacity-100"
                    />
                  </Link>
                ))
              ) : (
                <EmptyState title="No appointments today" />
              )}
            </section>
          </div>

          <section className="flex flex-col">
            <SectionHeader
              level="major"
              title="Recovery escalations"
              meta={escalated.length ? `${escalated.length} escalated` : undefined}
            />
            {escalated.length ? (
              escalated.slice(0, 5).map((episode) => (
                <Link
                  key={episode.id}
                  href={`/clinician/patients/${episode.patient_id}`}
                  className="focus-ink group grid min-h-[60px] grid-cols-[minmax(0,1fr)_auto_auto_auto] items-center gap-4 border-b border-rule py-3 pl-1 pr-1 hover:bg-hover"
                >
                  <span className="flex min-w-0 flex-col gap-[3px]">
                    <span className="truncate text-[0.9375rem] font-medium text-ink">
                      {names[episode.patient_id] ?? "Patient"}
                    </span>
                    <span className="truncate font-mono text-[11.5px] text-muted">
                      episode {episode.id.slice(0, 8)}
                    </span>
                  </span>
                  <StatusBadge status={episodeStatus(episode.status)} className="h-6" />
                  <StatusBadge status={riskStatus(episode.risk_level)} className="h-6" />
                  <Icon
                    name="chevronRight"
                    size={15}
                    className="text-muted opacity-0 group-hover:opacity-100"
                  />
                </Link>
              ))
            ) : (
              <EmptyState title="No escalated recoveries" />
            )}
          </section>

          <section className="flex flex-col">
            <SectionHeader
              level="major"
              title="Recent patients"
              actionHref="/clinician/patients"
              actionLabel="All patients"
            />
            {patients.length ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3">
                {patients.slice(0, 6).map((patient) => (
                  <Link
                    key={patient.id}
                    href={`/clinician/patients/${patient.id}`}
                    className="focus-ink group flex min-h-[60px] items-center justify-between gap-3 border-b border-rule px-1 py-3 hover:bg-hover"
                  >
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate text-[0.9375rem] font-medium text-ink">
                        {patient.name}
                      </span>
                      <span className="truncate font-mono text-[11.5px] text-muted">
                        {displayPatientId(patient.id)}
                      </span>
                    </span>
                    <Icon
                      name="chevronRight"
                      size={15}
                      className="text-muted opacity-0 group-hover:opacity-100"
                    />
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState title="No patients" />
            )}
          </section>

          <p className="mt-2 font-mono text-[0.75rem] text-muted">
            Demo environment · no real patient data
          </p>
        </>
      )}
    </>
  );
}
