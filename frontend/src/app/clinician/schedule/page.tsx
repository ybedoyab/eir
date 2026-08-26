"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { FilterChips } from "@/components/ui/FilterChips";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTime, formatWhen } from "@/lib/format";
import { appointmentStatus } from "@/lib/statusLabels";
import { listAppointments, listPatients } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { Patient } from "@/types";

type Range = "today" | "week";

export default function ClinicianSchedulePage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [range, setRange] = useState<Range>("today");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [appointmentItems, patientItems] = await Promise.all([
        listAppointments(),
        listPatients(),
      ]);
      setAppointments(appointmentItems);
      setPatients(patientItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load schedule");
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

  const rows = useMemo(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(end.getDate() + (range === "today" ? 1 : 7));
    return appointments
      .filter(
        (item) =>
          item.status !== "cancelled" &&
          new Date(item.start) >= start &&
          new Date(item.start) < end,
      )
      .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());
  }, [appointments, range]);

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Clinician workspace"
        title="Schedule"
        description="Today and the next seven days from the hospital appointment record."
        density="staff"
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      <FilterChips
        label="Schedule range"
        value={range}
        onChange={setRange}
        options={[
          { id: "today", label: "Today" },
          { id: "week", label: "Next 7 days" },
        ]}
      />
      <div className="mt-6">
        {loading ? (
          <CardSkeleton rows={6} />
        ) : rows.length ? (
          <div className="flex flex-col">
            <div className="hidden grid-cols-[92px_minmax(0,1fr)_150px_120px] items-baseline gap-4 border-b border-rule-strong pb-2.5 md:grid">
              <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                Time
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                Patient
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                Specialty
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                Status
              </span>
            </div>
            {rows.map((appointment) => (
              <Link
                key={appointment.id}
                href={`/clinician/patients/${appointment.patient_id}`}
                className="focus-ink grid min-h-[60px] items-center gap-2 border-b border-rule py-3 hover:bg-hover md:grid-cols-[92px_minmax(0,1fr)_150px_120px] md:gap-4 md:py-0"
              >
                <span className="font-mono text-[13px] text-ink">
                  {formatTime(appointment.start)}
                </span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="truncate text-[15px] text-ink">
                    {names[appointment.patient_id] ?? "Patient"}
                  </span>
                  <span className="truncate font-mono text-[11.5px] text-muted md:hidden">
                    {formatWhen(appointment.start)}
                  </span>
                  <span className="truncate font-mono text-[11.5px] text-muted">
                    {appointment.location_name}
                  </span>
                </span>
                <span className="truncate text-[14px] text-secondary">
                  {appointment.specialty}
                </span>
                <StatusBadge status={appointmentStatus(appointment.status)} />
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No appointments in this range"
            description="Nothing is booked in the window you selected."
          />
        )}
      </div>
    </section>
  );
}
