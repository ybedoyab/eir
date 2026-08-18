"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { loadSession } from "@/lib/auth";
import { listAppointments, listRecovery } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { RecoveryEpisode } from "@/types";

function formatWhen(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function PatientHomePage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const session = loadSession();
  const firstName = session?.display_name?.split(" ")[0] ?? "there";

  useEffect(() => {
    void listAppointments().then(setAppointments).catch(() => setAppointments([]));
    void listRecovery()
      .then((items) => setEpisodes(items.filter((item) => item.patient_id === session?.patient_id)))
      .catch(() => setEpisodes([]));
  }, [session?.patient_id]);

  const nextAppointment = useMemo(
    () =>
      appointments
        .filter((item) => item.status !== "cancelled")
        .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())[0],
    [appointments],
  );

  const activeRecovery = episodes.find((item) => !["COMPLETED", "CANCELLED"].includes(item.status));

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Patient portal"
        title={`Good morning, ${firstName}`}
        description="Manage appointments, recovery follow-up, and talk to EIR."
        actions={
          <Link href="/patient/assistant">
            <Button>Talk to EIR</Button>
          </Link>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Next appointment" description="Your nearest upcoming visit." />
          {nextAppointment ? (
            <div className="space-y-3">
              <div>
                <p className="text-lg font-semibold text-slate-900">{nextAppointment.specialty}</p>
                <p className="text-sm text-slate-600">{nextAppointment.practitioner_name}</p>
                <p className="mt-2 text-sm text-slate-700">{formatWhen(nextAppointment.start)}</p>
                <p className="text-sm text-slate-500">{nextAppointment.location_name}</p>
              </div>
              <Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">Confirmed</Badge>
              <div className="flex flex-wrap gap-2 pt-2">
                <Link href="/patient/appointments">
                  <Button variant="secondary">Manage appointment</Button>
                </Link>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No upcoming appointments"
              description="Schedule a visit when you are ready."
              action={
                <Link href="/patient/appointments">
                  <Button>Schedule appointment</Button>
                </Link>
              }
            />
          )}
        </Card>

        <Card>
          <CardHeader title="Recovery" description="Longitudinal follow-up after a procedure or discharge." />
          {activeRecovery ? (
            <div className="space-y-3">
              <Badge className="bg-teal-50 text-teal-800 ring-teal-200">{activeRecovery.status}</Badge>
              <p className="text-sm text-slate-600">
                Risk level: <span className="font-medium text-slate-900">{activeRecovery.risk_level}</span>
              </p>
              <Link href={`/recovery/${activeRecovery.id}`}>
                <Button variant="secondary">Open recovery episode</Button>
              </Link>
            </div>
          ) : (
            <EmptyState
              title="No active recovery episode"
              description="Start recovery follow-up when you need post-discharge support."
              action={
                <Link href="/patient/recovery">
                  <Button variant="secondary">View recovery</Button>
                </Link>
              }
            />
          )}
        </Card>
      </div>

      <Card>
        <CardHeader title="Quick actions" />
        <div className="flex flex-wrap gap-3">
          <Link href="/patient/appointments?action=schedule">
            <Button variant="secondary">Schedule appointment</Button>
          </Link>
          <Link href="/patient/appointments?action=reschedule">
            <Button variant="secondary">Reschedule</Button>
          </Link>
          <Link href="/patient/appointments?action=cancel">
            <Button variant="secondary">Cancel</Button>
          </Link>
          <Link href="/patient/assistant">
            <Button>Ask EIR</Button>
          </Link>
        </div>
      </Card>
    </section>
  );
}
