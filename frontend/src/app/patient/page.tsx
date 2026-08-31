"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AppointmentCard } from "@/components/ui/AppointmentCard";
import { ActionLink } from "@/components/ui/ActionLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { APP_ROUTE_BUILDERS, APP_ROUTES } from "@/config/app";
import { loadSession } from "@/lib/auth";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { firstName, formatWhen, greeting } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import { listAppointments, listRecovery } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { RecoveryEpisode } from "@/types";

export default function PatientHomePage() {
  const [session, setSession] = useState<ReturnType<typeof loadSession>>(null);
  const name = firstName(session?.display_name ?? "there");
  const pageTitle = session ? `${greeting(name)}.` : "Welcome.";
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => setSession(loadSession()), []);

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
      setError(getErrorMessage(err, ERROR_MESSAGES.patientHome));
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
      <PageHeader
        eyebrow="Your care"
        title={pageTitle}
        description={checkInDue ? "One thing needs you today." : "Your visits, recovery and hospital assistant in one place."}
        density="patient"
        icon="heart"
      />

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      {loading ? (
        <div className="flex flex-col gap-10">
          <CardSkeleton rows={4} />
          <CardSkeleton rows={4} />
        </div>
      ) : (
        <>
          {activeRecovery ? (
            <section
              className={`eir-surface eir-card-hover on-tint relative flex flex-col gap-8 overflow-hidden border-l-[4px] bg-gradient-to-br from-accent-tint via-surface to-sky px-7 py-7 lg:flex-row lg:items-center lg:justify-between ${
                checkInDue ? "border-warn" : "border-accent"
              }`}
            >
              <span className="eir-orb eir-drift pointer-events-none absolute -right-10 -top-10 h-32 w-32 opacity-10" aria-hidden />
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
              <ActionLink
                href={APP_ROUTES.patient.recovery}
                className="relative min-h-14 shrink-0 px-8 text-[1rem]"
              >
                {checkInDue ? "Start check-in" : "Open recovery"}
                <Icon name="arrowRight" size={16} />
              </ActionLink>
            </section>
          ) : null}

          <section className="flex flex-col">
            <SectionHeader
              level="major"
              title="Appointments"
              actionHref={APP_ROUTES.patient.appointments}
              actionLabel="See all"
            />
            {nextTwo.length ? (
              nextTwo.map((appointment) => (
                <AppointmentCard
                  key={appointment.id}
                  appointment={appointment}
                  actions={
                    <ActionLink
                      href={APP_ROUTE_BUILDERS.patientAppointments("reschedule")}
                      variant="secondary"
                      className="px-4"
                    >
                      Reschedule
                      <Icon name="chevronRight" size={14} className="text-muted" />
                    </ActionLink>
                  }
                />
              ))
            ) : (
              <EmptyState
                title="No upcoming appointments"
                description="Schedule a visit when you are ready."
                action={
                  <ActionLink href={APP_ROUTE_BUILDERS.patientAppointments("schedule")}>
                    Schedule appointment
                    <Icon name="arrowRight" size={16} />
                  </ActionLink>
                }
              />
            )}
          </section>

          <section className="grid gap-10 lg:grid-cols-3">
            <div className="flex flex-col lg:col-span-2">
              <SectionHeader level="major" title="Your recovery so far" />
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
                    <ActionLink href={APP_ROUTES.patient.recovery} variant="secondary">
                      Open recovery
                      <Icon name="chevronRight" size={15} />
                    </ActionLink>
                  }
                />
              )}
            </div>

            <div className="flex flex-col">
              <SectionHeader level="major" title="Assistant" />
              <p className="text-[0.9375rem] leading-[1.65] text-secondary">
                Ask about appointments, transport or what to expect this week. Anything clinical
                goes straight to a person.
              </p>
              <ActionLink
                href={APP_ROUTES.patient.assistant}
                variant="secondary"
                className="mt-5 min-h-14 px-6 text-[0.9375rem]"
              >
                Ask a question
                <Icon name="arrowRight" size={16} />
              </ActionLink>
              <ActionLink
                href={APP_ROUTE_BUILDERS.patientAppointments("schedule")}
                variant="ghost"
                className="mt-3 min-h-14 border border-rule px-6 text-[0.9375rem]"
              >
                <Icon name="plus" size={16} />
                Schedule a visit
              </ActionLink>
            </div>
          </section>
        </>
      )}
    </>
  );
}
