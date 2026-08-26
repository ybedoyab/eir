"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SearchInput } from "@/components/ui/SearchInput";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatWhen } from "@/lib/format";
import { episodeStatus } from "@/lib/statusLabels";
import { listAppointments, listPatients, listRecovery, listReviews } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { HumanReview, Patient, RecoveryEpisode } from "@/types";

export function PatientDirectory({
  eyebrow,
  title,
  hrefFor,
}: {
  eyebrow: string;
  title: string;
  hrefFor: (id: string) => string;
}) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [patientItems, appointmentItems, episodeItems, reviewItems] = await Promise.all([
        listPatients(),
        listAppointments(),
        listRecovery(),
        listReviews(true),
      ]);
      setPatients(patientItems);
      setAppointments(appointmentItems);
      setEpisodes(episodeItems);
      setReviews(reviewItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load patients");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return patients
      .filter((patient) => !q || patient.name.toLowerCase().includes(q))
      .map((patient) => {
        const next = appointments
          .filter(
            (item) =>
              item.patient_id === patient.id &&
              item.status !== "cancelled" &&
              new Date(item.end).getTime() >= Date.now(),
          )
          .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())[0];
        const recovery = episodes.find(
          (item) =>
            item.patient_id === patient.id && !["COMPLETED", "CANCELLED"].includes(item.status),
        );
        const needsReview = reviews.some((review) =>
          episodes.some((item) => item.id === review.episode_id && item.patient_id === patient.id),
        );
        return { patient, next, recovery, needsReview };
      });
  }, [patients, appointments, episodes, reviews, query]);

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description="Synthetic hospital directory — no real patient data."
        density="staff"
      />

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      <SearchInput
        placeholder="Search by patient name"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="mb-6 max-w-md"
      />

      {loading ? (
        <CardSkeleton rows={6} />
      ) : rows.length ? (
        <div className="flex flex-col">
          <div className="grid grid-cols-[minmax(0,1fr)_180px] items-baseline gap-4 border-b border-rule-strong pb-2.5 sm:grid-cols-[minmax(0,1fr)_220px_200px]">
            <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
              Patient
            </span>
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.1em] text-muted sm:block">
              Next visit
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
              Recovery
            </span>
          </div>

          {rows.map(({ patient, next, recovery, needsReview }) => (
            <Link
              key={patient.id}
              href={hrefFor(patient.id)}
              className="focus-ink grid min-h-[60px] grid-cols-[minmax(0,1fr)_180px] items-center gap-4 border-b border-rule hover:bg-hover sm:grid-cols-[minmax(0,1fr)_220px_200px]"
            >
              <span className="flex min-w-0 items-center gap-3">
                <Avatar name={patient.name} size="sm" />
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="truncate text-[15px] text-ink">{patient.name}</span>
                  <span className="truncate font-mono text-[11px] text-muted">
                    {patient.preferred_language} · {patient.preferred_contact_channel}
                  </span>
                </span>
              </span>

              <span className="hidden truncate font-mono text-[12px] text-secondary sm:block">
                {next ? formatWhen(next.start) : "none scheduled"}
              </span>

              <span className="flex flex-wrap items-center justify-end gap-2 pr-1 sm:justify-start sm:pr-0">
                {recovery ? <StatusBadge status={episodeStatus(recovery.status)} /> : null}
                {needsReview ? (
                  <StatusBadge status={{ label: "Waiting review", tone: "warning" }} />
                ) : null}
                {!recovery && !needsReview ? (
                  <span className="font-mono text-[11.5px] text-inactive">no episode</span>
                ) : null}
                <Icon name="chevronRight" size={14} className="ml-auto text-muted sm:hidden" />
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No matching patients"
          description="Nothing in the synthetic directory matches that name."
        />
      )}
    </section>
  );
}
