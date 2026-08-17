"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
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
    <section>
      <PageHeader
        eyebrow="Synthetic cohort"
        title="Patients"
        description="Synthetic patients only. No real PHI is stored or displayed."
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      {loading ? (
        <Card>
          <p className="text-sm text-slate-500">Loading patients…</p>
        </Card>
      ) : patients.length === 0 ? (
        <EmptyState
          title="No patients found"
          description="Seed synthetic FHIR fixtures or start the API to populate this list."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {patients.map((patient) => (
            <Link key={patient.id} href={`/patients/${patient.id}`} className="group">
              <Card className="h-full transition group-hover:-translate-y-0.5 group-hover:border-teal-200 group-hover:shadow-lg">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900 group-hover:text-teal-800">
                      {patient.name}
                    </h2>
                    <p className="mt-1 font-mono text-xs text-slate-400">{patient.id}</p>
                  </div>
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">Synthetic</Badge>
                </div>
                <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-slate-500">DOB</dt>
                    <dd className="mt-1 font-medium text-slate-800">{patient.date_of_birth}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Language</dt>
                    <dd className="mt-1 font-medium text-slate-800">{patient.preferred_language}</dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-slate-500">Preferred channel</dt>
                    <dd className="mt-1 font-medium capitalize text-slate-800">
                      {patient.preferred_contact_channel}
                    </dd>
                  </div>
                </dl>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
