"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { listPatients } from "@/services/api";
import type { Patient } from "@/types";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPatients()
      .then(setPatients)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Synthetic cohort"
        title="Patients"
        description="Synthetic patients only. No real PHI is stored or displayed."
        density="staff"
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      {loading ? (
        <CardSkeleton rows={6} />
      ) : patients.length === 0 ? (
        <EmptyState
          title="No patients found"
          description="Seed synthetic FHIR fixtures or start the API to populate this list."
        />
      ) : (
        <div className="flex flex-col">
          <div className="grid grid-cols-[minmax(0,1fr)_120px] items-baseline gap-4 border-b border-rule-strong pb-2.5 sm:grid-cols-[minmax(0,1fr)_140px_160px]">
            <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
              Patient
            </span>
            <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
              Born
            </span>
            <span className="hidden font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted sm:block">
              Reach them by
            </span>
          </div>

          {patients.map((patient) => (
            <Link
              key={patient.id}
              href={`/patients/${patient.id}`}
              className="focus-ink grid min-h-[60px] grid-cols-[minmax(0,1fr)_120px] items-center gap-4 border-b border-rule hover:bg-hover sm:grid-cols-[minmax(0,1fr)_140px_160px]"
            >
              <span className="flex min-w-0 items-center gap-3">
                <Avatar name={patient.name} size="sm" />
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="truncate text-[0.9375rem] text-ink">{patient.name}</span>
                  <span className="truncate font-mono text-[0.75rem] text-muted">{patient.id}</span>
                </span>
              </span>
              <span className="font-mono text-[0.75rem] text-secondary">
                {patient.date_of_birth}
              </span>
              <span className="hidden items-center gap-2 font-mono text-[0.75rem] text-secondary sm:flex">
                {patient.preferred_contact_channel} · {patient.preferred_language}
                <Icon name="chevronRight" size={14} className="ml-auto text-muted" />
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
