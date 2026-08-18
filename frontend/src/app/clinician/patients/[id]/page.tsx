"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import type { Appointment } from "@/lib/auth";
import { getPatient, listAppointments, listRecovery } from "@/services/api";
import type { Patient, RecoveryEpisode } from "@/types";

export default function ClinicianPatientDetailPage({ params }: { params: { id: string } }) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);

  useEffect(() => {
    void getPatient(params.id).then(setPatient);
    void listRecovery()
      .then((items) => setEpisodes(items.filter((item) => item.patient_id === params.id)))
      .catch(() => setEpisodes([]));
    void listAppointments()
      .then((items) => setAppointments(items.filter((item) => item.patient_id === params.id)))
      .catch(() => setAppointments([]));
  }, [params.id]);

  if (!patient) {
    return <p className="text-sm text-slate-500">Loading patient…</p>;
  }

  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Patient chart" title={patient.name} description={patient.id} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Upcoming appointments" />
          {appointments.map((appointment) => (
            <div key={appointment.id} className="mb-3 rounded-xl border border-slate-200 p-4">
              <p className="font-medium text-slate-900">{appointment.specialty}</p>
              <p className="text-sm text-slate-600">{appointment.start}</p>
            </div>
          ))}
        </Card>
        <Card>
          <CardHeader title="Active recovery" />
          {episodes.map((episode) => (
            <div key={episode.id} className="mb-3 flex items-center justify-between rounded-xl border border-slate-200 p-4">
              <div>
                <Badge className="bg-teal-50 text-teal-800 ring-teal-200">{episode.status}</Badge>
                <p className="mt-2 text-sm text-slate-600">Risk {episode.risk_level}</p>
              </div>
              <Link href={`/recovery/${episode.id}`} className="text-sm font-medium text-teal-700">
                Open episode
              </Link>
            </div>
          ))}
        </Card>
      </div>
    </section>
  );
}
