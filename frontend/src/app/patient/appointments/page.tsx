"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import type { Appointment, SlotOption } from "@/lib/auth";
import {
  bookAppointment,
  cancelAppointment,
  listAppointments,
  rescheduleAppointment,
  searchAvailability,
} from "@/services/api";

function formatWhen(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function PatientAppointmentsPage() {
  const searchParams = useSearchParams();
  const action = searchParams.get("action");
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [slots, setSlots] = useState<SlotOption[]>([]);
  const [selectedAppointment, setSelectedAppointment] = useState<string>("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"upcoming" | "past" | "cancelled">("upcoming");

  async function refresh() {
    setError(null);
    try {
      setAppointments(await listAppointments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load appointments");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (action === "schedule") {
      void searchAvailability({ specialty: "Cardiology" })
        .then(setSlots)
        .catch(() => setSlots([]));
    }
  }, [action]);

  const filtered = useMemo(() => {
    const now = Date.now();
    if (tab === "cancelled") {
      return appointments.filter((item) => item.status === "cancelled");
    }
    if (tab === "past") {
      return appointments.filter(
        (item) => item.status !== "cancelled" && new Date(item.end).getTime() < now,
      );
    }
    return appointments.filter(
      (item) => item.status !== "cancelled" && new Date(item.end).getTime() >= now,
    );
  }, [appointments, tab]);

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Appointment center"
        title="Your appointments"
        description="View, schedule, reschedule, or cancel visits."
      />
      {error ? <ErrorAlert message={error} /> : null}
      {message ? (
        <Card className="border-emerald-200 bg-emerald-50">
          <p className="text-sm font-medium text-emerald-900">{message}</p>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {(["upcoming", "past", "cancelled"] as const).map((value) => (
          <Button
            key={value}
            variant={tab === value ? "primary" : "secondary"}
            onClick={() => setTab(value)}
          >
            {value[0].toUpperCase() + value.slice(1)}
          </Button>
        ))}
      </div>

      <div className="grid gap-4">
        {filtered.length ? (
          filtered.map((appointment) => (
            <Card key={appointment.id}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-lg font-semibold text-slate-900">{appointment.specialty}</p>
                  <p className="text-sm text-slate-600">{appointment.practitioner_name}</p>
                  <p className="mt-2 text-sm text-slate-700">{formatWhen(appointment.start)}</p>
                  <p className="text-sm text-slate-500">{appointment.location_name}</p>
                  <Badge className="mt-3 bg-slate-50 text-slate-700 ring-slate-200">
                    {appointment.status}
                  </Badge>
                </div>
                {appointment.status !== "cancelled" ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        setSelectedAppointment(appointment.id);
                        setSlots(await searchAvailability({ specialty: appointment.specialty }));
                      }}
                    >
                      Reschedule
                    </Button>
                    <Button
                      variant="danger"
                      onClick={async () => {
                        if (!window.confirm("Cancel this appointment?")) return;
                        await cancelAppointment(appointment.id, "patient requested cancellation");
                        setMessage("Appointment cancelled.");
                        await refresh();
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : null}
              </div>
            </Card>
          ))
        ) : (
          <EmptyState title="No appointments in this tab" />
        )}
      </div>

      {action === "schedule" || slots.length ? (
        <Card>
          <CardHeader
            title={selectedAppointment ? "Choose a new time" : "Available times"}
            description="Select a slot to book or reschedule."
          />
          <div className="grid gap-3">
            {slots.map((slot) => (
              <div
                key={slot.id}
                className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="font-medium text-slate-900">{slot.service_name}</p>
                  <p className="text-sm text-slate-600">
                    {formatWhen(slot.start)} · {slot.location_name}
                  </p>
                </div>
                <Button
                  onClick={async () => {
                    if (selectedAppointment) {
                      await rescheduleAppointment(selectedAppointment, slot.id);
                      setMessage("Appointment rescheduled.");
                    } else {
                      await bookAppointment(slot.id);
                      setMessage("Appointment booked.");
                    }
                    setSlots([]);
                    setSelectedAppointment("");
                    await refresh();
                  }}
                >
                  {selectedAppointment ? "Confirm reschedule" : "Book"}
                </Button>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      <Link href="/patient/assistant" className="text-sm font-medium text-teal-700 hover:text-teal-800">
        Prefer conversation? Ask EIR to schedule for you
      </Link>
    </section>
  );
}
