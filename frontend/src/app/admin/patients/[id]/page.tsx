"use client";

import { use } from "react";

import { PatientChart } from "@/components/PatientChart";

export default function AdminPatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <PatientChart patientId={id} />;
}
