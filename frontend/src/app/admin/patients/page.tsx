"use client";

import { PatientDirectory } from "@/components/PatientDirectory";

export default function AdminPatientsPage() {
  return (
    <PatientDirectory
      eyebrow="Operations"
      title="Patient directory"
      hrefFor={(id) => `/admin/patients/${id}`}
    />
  );
}
