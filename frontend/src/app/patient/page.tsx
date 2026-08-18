"use client";

import {
  CalendarDays,
  HeartPulse,
  MessageCircle,
  CalendarPlus,
  CalendarClock,
  CalendarX,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppointmentCard } from "@/components/ui/AppointmentCard";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { loadSession } from "@/lib/auth";
import { firstName, formatWhen, greeting } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import { listAppointments, listRecovery } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { RecoveryEpisode } from "@/types";

export default function PatientHomePage() {
  const session = loadSession();
  const name = firstName(session?.display_name ?? "there");
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextAppointments, allEpisodes] = await Promise.all([
        listAppointments(),
        listRecovery(),
      ]);
      setAppointments(nextAppointments);
      setEpisodes(allEpisodes.filter((item) => item.patient_id === session?.patient_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your home");
    } finally {
      setLoading(false);
    }
  }, [session?.patient_id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const upcoming = useMemo(
    () =>
      appointments
        .filter((item) => item.status !== "cancelled" && new Date(item.end).getTime() >= Date.now())
        .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime()),
    [appointments],
  );
  const nextAppointment = upcoming[0];
  const later = upcoming.slice(1, 3);
  const activeRecovery = episodes.find((item) => !["COMPLETED", "CANCELLED"].includes(item.status));

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Patient portal"
        title={greeting(name)}
        description="Your visits, recovery, and hospital assistant in one place."
        actions={
          <div className="flex items-center gap-3">
            <Avatar name={session?.display_name ?? name} size="lg" />
            <Link href="/patient/assistant">
              <Button>
                <MessageCircle aria-hidden className="h-4 w-4" />
                Ask EIR
              </Button>
            </Link>
          </div>
        }
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <CardSkeleton rows={5} />
          <CardSkeleton rows={5} />
        </div>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="border-teal-100">
              <p className="text-xs font-medium uppercase tracking-wide text-teal-700">
                Next appointment
              </p>
              {nextAppointment ? (
                <div className="mt-3 space-y-3">
                  <AppointmentCard appointment={nextAppointment} className="shadow-none" />
                  <Link href="/patient/appointments">
                    <Button variant="secondary">Manage appointment</Button>
                  </Link>
                </div>
              ) : (
                <EmptyState
                  title="No upcoming appointments"
                  description="Schedule a visit when you are ready."
                  icon={CalendarDays}
                  action={
                    <Link href="/patient/appointments?action=schedule">
                      <Button>Schedule appointment</Button>
                    </Link>
                  }
                />
              )}
            </Card>

            <Card>
              <p className="text-xs font-medium uppercase tracking-wide text-teal-700">Recovery</p>
              {activeRecovery ? (
                <div className="mt-4 space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge status={episodeStatus(activeRecovery.status)} />
                    <StatusBadge status={riskStatus(activeRecovery.risk_level, "patient")} />
                  </div>
                  <p className="text-sm text-slate-600">
                    Next check-in{" "}
                    <span className="font-medium text-slate-900">
                      {activeRecovery.next_follow_up_at
                        ? formatWhen(activeRecovery.next_follow_up_at)
                        : "to be scheduled"}
                    </span>
                  </p>
                  <Link href="/patient/recovery">
                    <Button variant="secondary">
                      <HeartPulse aria-hidden className="h-4 w-4" />
                      View recovery details
                    </Button>
                  </Link>
                </div>
              ) : (
                <EmptyState
                  title="No active recovery"
                  description="Recovery follow-up appears here after a procedure or discharge."
                  icon={HeartPulse}
                  action={
                    <Link href="/patient/recovery">
                      <Button variant="secondary">Open recovery</Button>
                    </Link>
                  }
                />
              )}
            </Card>
          </div>

          {later.length ? (
            <Card>
              <p className="mb-4 text-xs font-medium uppercase tracking-wide text-slate-500">
                Upcoming
              </p>
              <div className="space-y-3">
                {later.map((item) => (
                  <div key={item.id} className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">{item.specialty}</p>
                      <p className="text-sm text-slate-500">{formatWhen(item.start)}</p>
                    </div>
                    <p className="text-sm text-slate-600">{item.practitioner_name}</p>
                  </div>
                ))}
              </div>
            </Card>
          ) : null}

          <Card>
            <p className="mb-4 text-xs font-medium uppercase tracking-wide text-slate-500">
              Quick actions
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Link href="/patient/appointments?action=schedule">
                <Button variant="secondary" className="w-full">
                  <CalendarPlus aria-hidden className="h-4 w-4" />
                  Schedule
                </Button>
              </Link>
              <Link href="/patient/appointments?action=reschedule">
                <Button variant="secondary" className="w-full">
                  <CalendarClock aria-hidden className="h-4 w-4" />
                  Reschedule
                </Button>
              </Link>
              <Link href="/patient/appointments?action=cancel">
                <Button variant="secondary" className="w-full">
                  <CalendarX aria-hidden className="h-4 w-4" />
                  Cancel
                </Button>
              </Link>
              <Link href="/patient/assistant">
                <Button className="w-full">
                  <MessageCircle aria-hidden className="h-4 w-4" />
                  Ask EIR
                </Button>
              </Link>
            </div>
          </Card>
        </>
      )}
    </section>
  );
}
