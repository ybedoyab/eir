"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { FilterChips } from "@/components/ui/FilterChips";
import { PageHeader } from "@/components/ui/PageHeader";
import { SearchInput } from "@/components/ui/SearchInput";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
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
      setError(getErrorMessage(err, ERROR_MESSAGES.appointments));
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
    <section className="flex flex-col gap-4">
      <PageHeader
        eyebrow="Operations"
        title="Appointment operations"
        description="Hospital-wide visits sorted by upcoming time."
        density="dense"
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      <SearchInput
        placeholder="Search patient, specialty, or clinician"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="max-w-md"
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
      <div className="mt-2">
        {loading ? (
          <CardSkeleton rows={6} />
        ) : rows.length ? (
          <div className="flex flex-col">
            <div className="hidden grid-cols-[150px_minmax(0,1fr)_120px_150px_130px_110px] items-baseline gap-4 border-b border-rule-strong pb-2.5 lg:grid">
              {["Time", "Patient", "Specialty", "Clinician", "Location", "Status"].map((head) => (
                <span
                  key={head}
                  className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted"
                >
                  {head}
                </span>
              ))}
            </div>
            {rows.map((appointment) => (
              <div
                key={appointment.id}
                className="grid min-h-11 items-center gap-1 border-b border-rule py-2.5 lg:grid-cols-[150px_minmax(0,1fr)_120px_150px_130px_110px] lg:gap-4 lg:py-0"
              >
                <span className="truncate font-mono text-[0.75rem] text-secondary">
                  {formatWhen(appointment.start)}
                </span>
                <span className="truncate text-[0.875rem] text-ink">
                  {names[appointment.patient_id] ?? "Patient"}
                </span>
                <span className="truncate text-[13.5px] text-secondary">
                  {appointment.specialty}
                </span>
                <span className="truncate text-[13.5px] text-secondary">
                  {appointment.practitioner_name}
                </span>
                <span className="truncate font-mono text-[11.5px] text-muted">
                  {appointment.location_name}
                </span>
                <StatusBadge status={appointmentStatus(appointment.status)} />
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No matching appointments"
            description="Nothing matches the filters you have applied."
          />
        )}
      </div>
    </section>
  );
}
