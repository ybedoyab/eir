"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppointmentCard } from "@/components/ui/AppointmentCard";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { loadSession } from "@/lib/auth";
import { firstName, formatWhen, greeting } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import { listAppointments, listRecovery } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { RecoveryEpisode } from "@/types";

export default function PatientHomePage() {
  // Read once per mount; `loadSession` hits localStorage + JSON.parse, and these
  // pages re-render on every fetch/state tick.
  const [session] = useState(loadSession);
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
  const nextTwo = upcoming.slice(0, 2);
  const activeRecovery = episodes.find((item) => !["COMPLETED", "CANCELLED"].includes(item.status));
  const checkInDue =
    activeRecovery?.status === "WAITING" || activeRecovery?.status === "WAITING_FOR_NEXT_FOLLOWUP";

  return (
    <>
      <header>
        <h1 className="font-serif text-[2.5rem] font-medium leading-[1.15] tracking-[-0.018em] text-ink">
          {greeting(name)}.
        </h1>
        <p className="mt-3 text-[1.0625rem] leading-[1.6] text-secondary">
          {checkInDue
            ? "One thing needs you today."
            : "Your visits, recovery and hospital assistant in one place."}
        </p>
      </header>

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <div className="flex flex-col gap-10">
          <CardSkeleton rows={4} />
          <CardSkeleton rows={4} />
        </div>
      ) : (
        <>
          {/* the one action */}
          {activeRecovery ? (
            <section
              className={`on-raised flex flex-col gap-8 border-l-[3px] bg-raised px-9 py-8 lg:flex-row lg:items-center lg:justify-between ${
                checkInDue ? "border-warn" : "border-accent"
              }`}
            >
              <div className="flex flex-col gap-2.5">
                <span
                  className={`font-mono text-[0.75rem] uppercase tracking-[0.1em] ${
                    checkInDue ? "text-warn" : "text-accent"
                  }`}
                >
                  {checkInDue ? "Check-in due" : "Recovery in progress"}
                </span>
                <h2 className="font-serif text-[1.6875rem] font-medium leading-[1.25] text-ink">
                  How is your recovery going today?
                </h2>
                <p className="max-w-[44ch] text-[1rem] leading-[1.6] text-secondary">
                  A few short questions about pain, swelling and movement. Takes about a minute. A
                  nurse reads anything that looks concerning.
                </p>
                <p className="mt-1 text-[0.875rem] text-secondary">
                  Next check-in{" "}
                  <span className="font-mono text-[0.8125rem] text-ink">
                    {activeRecovery.next_follow_up_at
                      ? formatWhen(activeRecovery.next_follow_up_at)
                      : "to be scheduled"}
                  </span>
                </p>
              </div>
              <Link
                href="/patient/recovery"
                className="focus-ink inline-flex min-h-14 shrink-0 items-center gap-2.5 bg-accent px-8 text-[1rem] font-medium text-paper hover:bg-accent-hover"
              >
                {checkInDue ? "Start check-in" : "Open recovery"}
                <Icon name="arrowRight" size={16} />
              </Link>
            </section>
          ) : null}

          {/* appointments */}
          <section className="flex flex-col">
            <SectionHeader
              title="Appointments"
              actionHref="/patient/appointments"
              actionLabel="See all"
            />
            {nextTwo.length ? (
              nextTwo.map((appointment) => (
                <AppointmentCard
                  key={appointment.id}
                  appointment={appointment}
                  actions={
                    <Link
                      href="/patient/appointments?action=reschedule"
                      className="focus-ink inline-flex min-h-11 items-center gap-2 border border-rule-strong px-4 text-sm font-medium text-body hover:bg-hover"
                    >
                      Reschedule
                      <Icon name="chevronRight" size={14} className="text-muted" />
                    </Link>
                  }
                />
              ))
            ) : (
              <EmptyState
                title="No upcoming appointments"
                description="Schedule a visit when you are ready."
                action={
                  <Link href="/patient/appointments?action=schedule">
                    <Button>
                      Schedule appointment
                      <Icon name="arrowRight" size={16} />
                    </Button>
                  </Link>
                }
              />
            )}
          </section>

          {/* recovery so far + assistant */}
          <section className="grid gap-10 lg:grid-cols-3">
            <div className="flex flex-col lg:col-span-2">
              <SectionHeader title="Your recovery so far" />
              {activeRecovery ? (
                <div className="flex flex-col">
                  <div className="grid grid-cols-[108px_minmax(0,1fr)_auto] items-center gap-5 border-b border-rule py-[18px]">
                    <span className="font-mono text-[0.8125rem] text-muted">Status</span>
                    <span className="text-[0.9375rem] leading-[1.6] text-body">
                      Episode {activeRecovery.id.slice(0, 8)}
                    </span>
                    <StatusBadge status={episodeStatus(activeRecovery.status)} />
                  </div>
                  <div className="grid grid-cols-[108px_minmax(0,1fr)_auto] items-center gap-5 border-b border-rule py-[18px]">
                    <span className="font-mono text-[0.8125rem] text-muted">How you are</span>
                    <span className="text-[0.9375rem] leading-[1.6] text-body">
                      Based on your last check-in
                    </span>
                    <StatusBadge status={riskStatus(activeRecovery.risk_level, "patient")} />
                  </div>
                  <div className="grid grid-cols-[108px_minmax(0,1fr)_auto] items-center gap-5 border-b border-rule py-[18px]">
                    <span className="font-mono text-[0.8125rem] text-muted">Started</span>
                    <span className="text-[0.9375rem] leading-[1.6] text-body">
                      {formatWhen(activeRecovery.started_at)}
                    </span>
                    <span className="font-mono text-[0.75rem] text-muted">—</span>
                  </div>
                </div>
              ) : (
                <EmptyState
                  title="No active recovery"
                  description="Recovery follow-up appears here after a procedure or discharge."
                  action={
                    <Link href="/patient/recovery">
                      <Button variant="secondary">
                        Open recovery
                        <Icon name="chevronRight" size={15} />
                      </Button>
                    </Link>
                  }
                />
              )}
            </div>

            <div className="flex flex-col">
              <SectionHeader title="Assistant" />
              <p className="text-[0.9375rem] leading-[1.65] text-secondary">
                Ask about appointments, transport or what to expect this week. Anything clinical
                goes straight to a person.
              </p>
              <Link
                href="/patient/assistant"
                className="focus-ink mt-5 inline-flex min-h-14 items-center justify-center gap-2.5 border border-rule-strong px-6 text-[0.9375rem] font-medium text-body hover:bg-hover"
              >
                Ask a question
                <Icon name="arrowRight" size={16} className="text-accent" />
              </Link>
              <Link
                href="/patient/appointments?action=schedule"
                className="focus-ink mt-3 inline-flex min-h-14 items-center justify-center gap-2.5 border border-rule px-6 text-[0.9375rem] text-secondary hover:bg-hover hover:text-ink"
              >
                <Icon name="plus" size={16} />
                Schedule a visit
              </Link>
            </div>
          </section>
        </>
      )}
    </>
  );
}
