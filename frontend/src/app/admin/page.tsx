"use client";

import {
  CalendarDays,
  ClipboardCheck,
  HeartPulse,
  LayoutGrid,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
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
      setError(err instanceof Error ? err.message : "Could not load operations");
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
    const items: Array<{ id: string; title: string; detail: string }> = [];
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
      });
    }
    for (const episode of recoveries.filter((item) => item.status === "ESCALATED")) {
      items.push({
        id: `esc-${episode.id}`,
        title: "Recovery escalation",
        detail: names[episode.patient_id] ?? "Patient",
      });
    }
    return items.slice(0, 8);
  }, [appointments, reviews, recoveries, names]);

  const activeRecoveries = recoveries.filter(
    (item) => !["COMPLETED", "CANCELLED"].includes(item.status),
  ).length;
  const pendingReviews = reviews.filter((item) => item.status === "pending").length;

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Operations"
        title="Hospital Operations Command Center"
        description="Metrics computed from stored synthetic hospital data."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <CardSkeleton rows={2} />
          <CardSkeleton rows={2} />
          <CardSkeleton rows={2} />
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard
              label="Appointments today"
              value={snapshot?.appointments.today_appointments ?? 0}
              icon={CalendarDays}
            />
            <StatCard
              label="Appointments next 7 days"
              value={snapshot?.appointments.next_7_days ?? 0}
              icon={LayoutGrid}
            />
            <StatCard
              label="Open slots"
              value={snapshot?.appointments.open_slots ?? 0}
              icon={CalendarDays}
            />
            <StatCard
              label="Waitlist requests"
              value={snapshot?.waitlist_requests ?? 0}
              icon={Users}
            />
            <StatCard label="Active recoveries" value={activeRecoveries} icon={HeartPulse} />
            <StatCard label="Reviews waiting" value={pendingReviews} icon={ClipboardCheck} />
          </div>
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">Operational activity</h2>
              <Link href="/admin/appointments" className="text-sm font-medium text-teal-700">
                View all
              </Link>
            </div>
            {activity.length ? (
              <ul className="space-y-3">
                {activity.map((item) => (
                  <li key={item.id} className="rounded-xl border border-slate-200 px-4 py-3">
                    <p className="text-sm font-medium text-slate-900">{item.title}</p>
                    <p className="text-sm text-slate-600">{item.detail}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="No recent operational activity" />
            )}
          </Card>
        </>
      )}
    </section>
  );
}
