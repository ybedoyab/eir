"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listPatients } from "@/services/api";
import type { Patient } from "@/types";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPatients()
      .then(setPatients)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section>
      <h1>Patients</h1>
      <p>Synthetic patients only. No real PHI.</p>
      {error ? <p>API unavailable: {error}</p> : null}
      <ul>
        {patients.map((patient) => (
          <li key={patient.id}>
            <Link href={`/patients/${patient.id}`}>
              {patient.name} ({patient.id})
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
