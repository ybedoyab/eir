"use client";

import { PatientDirectory } from "@/components/PatientDirectory";

export default function ClinicianPatientsPage() {
  return (
    <PatientDirectory
      eyebrow="Clinician workspace"
      title="Patients"
      hrefFor={(id) => `/clinician/patients/${id}`}
    />
  );
}
