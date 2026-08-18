"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { FilterChips } from "@/components/ui/FilterChips";
import { PageHeader } from "@/components/ui/PageHeader";
import { SearchInput } from "@/components/ui/SearchInput";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatWhen, LOCATIONS, SPECIALTIES } from "@/lib/format";
import { appointmentStatus } from "@/lib/statusLabels";
import { listAppointments, listPatients } from "@/services/api";
import type { Appointment } from "@/lib/auth";
import type { Patient } from "@/types";

export default function AdminAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [specialty, setSpecialty] = useState("all");
  const [location, setLocation] = useState("all");
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
      setError(err instanceof Error ? err.message : "Could not load appointments");
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
    const q = query.trim().toLowerCase();
    return appointments
      .filter((item) => {
        const patientName = names[item.patient_id] ?? "";
        const matchesQuery =
          !q ||
          patientName.toLowerCase().includes(q) ||
          item.specialty.toLowerCase().includes(q) ||
          item.practitioner_name.toLowerCase().includes(q);
        const matchesStatus = status === "all" || item.status === status;
        const matchesSpecialty = specialty === "all" || item.specialty === specialty;
        const matchesLocation = location === "all" || item.location_name === location;
        return matchesQuery && matchesStatus && matchesSpecialty && matchesLocation;
      })
      .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());
  }, [appointments, names, query, status, specialty, location]);

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Appointment operations"
        description="Hospital-wide visits sorted by upcoming time."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      <SearchInput
        placeholder="Search patient, specialty, or clinician"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <FilterChips
        label="Status"
        value={status}
        onChange={setStatus}
        options={[
          { id: "all", label: "All statuses" },
          { id: "booked", label: "Confirmed" },
          { id: "fulfilled", label: "Completed" },
          { id: "cancelled", label: "Cancelled" },
        ]}
      />
      <FilterChips
        label="Specialty"
        value={specialty}
        onChange={setSpecialty}
        options={[
          { id: "all", label: "All specialties" },
          ...SPECIALTIES.map((item) => ({ id: item, label: item })),
        ]}
      />
      <FilterChips
        label="Location"
        value={location}
        onChange={setLocation}
        options={[
          { id: "all", label: "All locations" },
          ...LOCATIONS.map((item) => ({ id: item, label: item })),
        ]}
      />
      {loading ? (
        <CardSkeleton rows={6} />
      ) : rows.length ? (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[var(--eir-shadow)]">
          <div className="hidden grid-cols-[9rem_1fr_8rem_9rem_8rem_7rem] gap-3 border-b border-slate-100 px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500 lg:grid">
            <span>Time</span>
            <span>Patient</span>
            <span>Specialty</span>
            <span>Clinician</span>
            <span>Location</span>
            <span>Status</span>
          </div>
          {rows.map((appointment) => (
            <div
              key={appointment.id}
              className="grid gap-1 border-b border-slate-100 px-4 py-4 last:border-0 lg:grid-cols-[9rem_1fr_8rem_9rem_8rem_7rem] lg:items-center"
            >
              <p className="text-sm font-medium text-slate-900">{formatWhen(appointment.start)}</p>
              <p className="font-medium text-slate-900">
                {names[appointment.patient_id] ?? "Patient"}
              </p>
              <p className="text-sm text-slate-700">{appointment.specialty}</p>
              <p className="text-sm text-slate-700">{appointment.practitioner_name}</p>
              <p className="text-sm text-slate-500">{appointment.location_name}</p>
              <StatusBadge status={appointmentStatus(appointment.status)} />
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No matching appointments" />
      )}
    </section>
  );
}
