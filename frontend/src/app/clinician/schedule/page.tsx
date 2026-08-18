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
    <section className="space-y-6">
      <PageHeader
        eyebrow="Clinician workspace"
        title="Schedule"
        description="Today and the next seven days from the hospital appointment record."
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
      {loading ? (
        <CardSkeleton rows={6} />
      ) : rows.length ? (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[var(--eir-shadow)]">
          <div className="hidden grid-cols-[7rem_1fr_10rem_8rem] gap-3 border-b border-slate-100 px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500 md:grid">
            <span>Time</span>
            <span>Patient</span>
            <span>Specialty</span>
            <span>Status</span>
          </div>
          {rows.map((appointment) => (
            <Link
              key={appointment.id}
              href={`/clinician/patients/${appointment.patient_id}`}
              className="grid gap-2 border-b border-slate-100 px-4 py-4 last:border-0 hover:bg-teal-50/40 md:grid-cols-[7rem_1fr_10rem_8rem] md:items-center"
            >
              <p className="text-sm font-medium text-slate-900">{formatTime(appointment.start)}</p>
              <div>
                <p className="font-medium text-slate-900">
                  {names[appointment.patient_id] ?? "Patient"}
                </p>
                <p className="text-sm text-slate-500 md:hidden">{formatWhen(appointment.start)}</p>
                <p className="text-sm text-slate-500">{appointment.location_name}</p>
              </div>
              <p className="text-sm text-slate-700">{appointment.specialty}</p>
              <StatusBadge status={appointmentStatus(appointment.status)} />
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No appointments in this range" />
      )}
    </section>
  );
}
