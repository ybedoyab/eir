"use client";

import { useEffect, useState } from "react";

import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { listAppointments } from "@/services/api";
import type { Appointment } from "@/lib/auth";

export default function AdminAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  useEffect(() => {
    void listAppointments().then(setAppointments).catch(() => setAppointments([]));
  }, []);

  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Operations" title="Appointment operations" />
      <div className="grid gap-4">
        {appointments.map((appointment) => (
          <Card key={appointment.id}>
            <CardHeader
              title={`${appointment.specialty} · ${appointment.patient_id}`}
              description={`${appointment.start} · ${appointment.status}`}
            />
          </Card>
        ))}
      </div>
    </section>
  );
}
