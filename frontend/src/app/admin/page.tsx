"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatCard, StatStrip } from "@/components/ui/StatCard";
import { APP_ROUTES } from "@/config/app";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { formatWhen } from "@/lib/format";
import type { AdminSnapshot, Appointment } from "@/lib/auth";
import {
  getAdminSnapshot,
  listAppointments,
  listPatients,
  listRecovery,
  listReviews,
} from "@/services/api";
import type { HumanReview, Patient, RecoveryEpisode } from "@/types";

export default function AdminHomePage() {
  const [snapshot, setSnapshot] = useState<AdminSnapshot | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [recoveries, setRecoveries] = useState<RecoveryEpisode[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [snap, appointmentItems, episodeItems, reviewItems, patientItems] = await Promise.all([
        getAdminSnapshot(),
        listAppointments(),
        listRecovery(),
        listReviews(false),
        listPatients(),
      ]);
      setSnapshot(snap);
      setAppointments(appointmentItems);
      setRecoveries(episodeItems);
      setReviews(reviewItems);
      setPatients(patientItems);
    } catch (err) {
      setError(getErrorMessage(err, ERROR_MESSAGES.operations));
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

  const activity = useMemo(() => {
    const items: Array<{ id: string; title: string; detail: string; tone?: string }> = [];
    for (const appointment of appointments) {
      if (appointment.status === "cancelled") {
        items.push({
          id: `cancel-${appointment.id}`,
          title: "Appointment cancelled",
          detail: `${names[appointment.patient_id] ?? "Patient"} · ${appointment.specialty} · ${formatWhen(appointment.start)}`,
        });
      }
    }
    for (const review of reviews) {
      items.push({
        id: `review-${review.id}`,
        title: review.status === "resolved" ? "Review resolved" : "Review opened",
        detail: review.reason,
        tone: review.status === "resolved" ? undefined : "text-warn",
      });
    }
    for (const episode of recoveries.filter((item) => item.status === "ESCALATED")) {
      items.push({
        id: `esc-${episode.id}`,
        title: "Recovery escalation",
        detail: names[episode.patient_id] ?? "Patient",
        tone: "text-high",
      });
    }
    return items.slice(0, 8);
  }, [appointments, reviews, recoveries, names]);

  const activeRecoveries = recoveries.filter(
    (item) => !["COMPLETED", "CANCELLED"].includes(item.status),
  ).length;
  const pendingReviews = reviews.filter((item) => item.status === "pending").length;

  return (
    <>
      <PageHeader
        eyebrow="Command center"
        title="Hospital operations"
        description="Every figure below is computed from stored hospital data."
        density="dense"
        icon="overview"
        actions={
          <Link href={APP_ROUTES.admin.fleet} className="focus-ink group inline-flex min-h-11 items-center gap-2 rounded-xl border border-accent/30 bg-surface/70 px-4 text-sm font-semibold text-accent shadow-[0_5px_16px_rgb(22_75_130/0.07)] hover:bg-accent-tint">
            Fleet and adapters
            <Icon name="arrowRight" size={14} />
          </Link>
        }
      />

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <CardSkeleton rows={4} />
      ) : (
        <>
          <StatStrip className="sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Reviews waiting"
              value={pendingReviews}
              tone={pendingReviews ? "high" : "ink"}
              hint={pendingReviews ? "workflows parked on a clinician" : "nothing parked"}
            />
            <StatCard
              label="Active recoveries"
              value={activeRecoveries}
              hint={`${recoveries.length} episodes on file`}
            />
            <StatCard
              label="Appointments today"
              value={snapshot?.appointments.today_appointments ?? 0}
              hint={`${snapshot?.appointments.open_slots ?? 0} open slots to fill`}
            />
            <StatCard
              label="Waitlist requests"
              value={snapshot?.waitlist_requests ?? 0}
              tone={snapshot?.waitlist_requests ? "warn" : "ink"}
              hint="patients waiting on a slot"
            />
          </StatStrip>

          <StatStrip className="sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Next 7 days"
              value={snapshot?.appointments.next_7_days ?? 0}
              hint="appointments already booked"
            />
            <StatCard
              label="Below reorder point"
              value={snapshot?.low_stock_skus ?? 0}
              tone={snapshot?.low_stock_skus ? "warn" : "ink"}
              hint={
                snapshot?.open_replenishments
                  ? `${snapshot.open_replenishments} replenishment case(s) in flight`
                  : "supply fleet idle"
              }
            />
            <StatCard
              label="POs to authorize"
              value={snapshot?.pending_purchase_approvals ?? 0}
              tone={snapshot?.pending_purchase_approvals ? "warn" : "ink"}
              hint="agents draft, a human authorizes"
            />
            <StatCard
              label="Patients on file"
              value={patients.length}
              hint="across every clinic"
            />
          </StatStrip>

          <section className="flex flex-col">
            <SectionHeader
              level="major"
              title="Operational activity"
              actionHref={APP_ROUTES.admin.appointments}
              actionLabel="Appointments"
            />
            {activity.length ? (
              <ul className="flex flex-col">
                {activity.map((item) => (
                  <li
                    key={item.id}
                    className="grid min-h-11 grid-cols-[minmax(0,1fr)] items-center gap-x-4 gap-y-1 border-b border-rule py-2 sm:grid-cols-[220px_minmax(0,1fr)]"
                  >
                    <span className={`text-[0.875rem] font-medium ${item.tone ?? "text-ink"}`}>
                      {item.title}
                    </span>
                    <span className="truncate text-[0.8125rem] text-secondary">{item.detail}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="No recent operational activity" />
            )}
          </section>

          <p className="font-mono text-[0.75rem] text-muted">
            Demo environment · no real patient data
          </p>
        </>
      )}
    </>
  );
}
