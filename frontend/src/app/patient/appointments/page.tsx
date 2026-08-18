"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { AppointmentCard } from "@/components/ui/AppointmentCard";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { FilterChips } from "@/components/ui/FilterChips";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import type { Appointment, SlotOption } from "@/lib/auth";
import { formatDateLong, formatTime, formatWhen, isMorning, SPECIALTIES } from "@/lib/format";
import {
  bookAppointment,
  cancelAppointment,
  listAppointments,
  rescheduleAppointment,
  searchAvailability,
} from "@/services/api";

type Tab = "upcoming" | "past" | "cancelled";
type DayPart = "any" | "morning" | "afternoon";

function groupSlots(slots: SlotOption[]): Array<{ label: string; slots: SlotOption[] }> {
  const groups = new Map<string, SlotOption[]>();
  for (const slot of slots) {
    const label = formatDateLong(slot.start);
    const list = groups.get(label) ?? [];
    list.push(slot);
    groups.set(label, list);
  }
  return Array.from(groups.entries()).map(([label, items]) => ({ label, slots: items }));
}

export default function PatientAppointmentsPage() {
  return (
    <Suspense
      fallback={
        <section className="space-y-6">
          <PageHeader title="Your appointments" description="Loading appointment workspace…" />
          <CardSkeleton rows={4} />
        </section>
      }
    >
      <PatientAppointmentsContent />
    </Suspense>
  );
}

function PatientAppointmentsContent() {
  const searchParams = useSearchParams();
  const action = searchParams.get("action");
  const { toast } = useToast();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [slots, setSlots] = useState<SlotOption[]>([]);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [pendingSlot, setPendingSlot] = useState<SlotOption | null>(null);
  const [cancelTarget, setCancelTarget] = useState<Appointment | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<Tab>(action === "cancel" ? "upcoming" : "upcoming");
  const [specialty, setSpecialty] = useState("Cardiology");
  const [dayPart, setDayPart] = useState<DayPart>("any");
  const [scheduling, setScheduling] = useState(action === "schedule");

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setAppointments(await listAppointments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load appointments");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSlots = useCallback(async (nextSpecialty = specialty, nextDayPart = dayPart) => {
    setSearching(true);
    try {
      const found = await searchAvailability({
        specialty: nextSpecialty,
        time_of_day: nextDayPart,
      });
      setSlots(found);
    } catch {
      setSlots([]);
    } finally {
      setSearching(false);
    }
  }, [specialty, dayPart]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (action === "schedule" || action === "reschedule") {
      setScheduling(true);
      void loadSlots();
    }
  }, [action, loadSlots]);

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

  const visibleSlots = useMemo(() => {
    if (dayPart === "morning") return slots.filter((slot) => isMorning(slot.start));
    if (dayPart === "afternoon") return slots.filter((slot) => !isMorning(slot.start));
    return slots;
  }, [slots, dayPart]);

  async function confirmPending() {
    if (!pendingSlot || busy) return;
    setBusy(true);
    try {
      if (selectedAppointment) {
        await rescheduleAppointment(selectedAppointment.id, pendingSlot.id);
        toast("Appointment rescheduled");
      } else {
        await bookAppointment(pendingSlot.id);
        toast("Appointment booked");
      }
      setPendingSlot(null);
      setSelectedAppointment(null);
      setSlots([]);
      setScheduling(false);
      await refresh();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not save appointment", "error");
    } finally {
      setBusy(false);
    }
  }

  async function confirmCancel() {
    if (!cancelTarget || busy) return;
    setBusy(true);
    try {
      await cancelAppointment(
        cancelTarget.id,
        cancelReason.trim() || "patient requested cancellation",
      );
      toast("Appointment cancelled");
      setCancelTarget(null);
      setCancelReason("");
      await refresh();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not cancel appointment", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Appointment center"
        title="Your appointments"
        description="View upcoming visits, find availability, and confirm changes before they are saved."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      <FilterChips
        label="Appointment list"
        value={tab}
        onChange={setTab}
        options={[
          { id: "upcoming", label: "Upcoming" },
          { id: "past", label: "Past" },
          { id: "cancelled", label: "Cancelled" },
        ]}
      />

      {loading ? (
        <CardSkeleton rows={4} />
      ) : filtered.length ? (
        <div className="grid gap-4">
          {filtered.map((appointment) => (
            <AppointmentCard
              key={appointment.id}
              appointment={appointment}
              actions={
                appointment.status !== "cancelled" && tab === "upcoming" ? (
                  <>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setSelectedAppointment(appointment);
                        setScheduling(true);
                        setSpecialty(appointment.specialty);
                        void loadSlots(appointment.specialty, dayPart);
                      }}
                    >
                      Reschedule
                    </Button>
                    <Button variant="danger" onClick={() => setCancelTarget(appointment)}>
                      Cancel
                    </Button>
                  </>
                ) : undefined
              }
            />
          ))}
        </div>
      ) : (
        <EmptyState title="No appointments in this tab" />
      )}

      <div className="flex flex-wrap gap-2">
        <Button
          variant={scheduling && !selectedAppointment ? "primary" : "secondary"}
          onClick={() => {
            setSelectedAppointment(null);
            setScheduling(true);
            void loadSlots();
          }}
        >
          Find a time
        </Button>
      </div>

      {scheduling ? (
        <Card>
          <CardHeader
            title={selectedAppointment ? "Choose a new time" : "Available times"}
            description="Select a slot, then confirm before booking or rescheduling."
          />
          <div className="mb-4 flex flex-col gap-3">
            <FilterChips
              label="Specialty"
              value={specialty}
              onChange={(value) => {
                setSpecialty(value);
                void loadSlots(value, dayPart);
              }}
              options={SPECIALTIES.map((item) => ({ id: item, label: item }))}
            />
            <FilterChips
              label="Time of day"
              value={dayPart}
              onChange={(value) => {
                setDayPart(value);
                void loadSlots(specialty, value);
              }}
              options={[
                { id: "any", label: "Any time" },
                { id: "morning", label: "Morning" },
                { id: "afternoon", label: "Afternoon" },
              ]}
            />
          </div>
          {searching ? (
            <CardSkeleton rows={3} />
          ) : visibleSlots.length ? (
            <div className="space-y-6">
              {groupSlots(visibleSlots).map((group) => (
                <div key={group.label}>
                  <h3 className="mb-2 text-sm font-semibold text-slate-800">{group.label}</h3>
                  <div className="flex flex-wrap gap-2">
                    {group.slots.map((slot) => (
                      <button
                        key={slot.id}
                        type="button"
                        onClick={() => setPendingSlot(slot)}
                        className="inline-flex min-h-11 flex-col rounded-xl border border-slate-200 bg-white px-4 py-2 text-left text-sm hover:border-teal-300 hover:bg-teal-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                      >
                        <span className="font-medium text-slate-900">{formatTime(slot.start)}</span>
                        <span className="text-xs text-slate-500">{slot.location_name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No open slots" description="Try another specialty or time of day." />
          )}
        </Card>
      ) : null}

      <Dialog
        open={Boolean(pendingSlot)}
        title={selectedAppointment ? "Confirm reschedule" : "Confirm booking"}
        description="Review the selected time before it is saved."
        onClose={() => setPendingSlot(null)}
      >
        {pendingSlot ? (
          <div className="space-y-4">
            {selectedAppointment ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Current
                  </p>
                  <p className="mt-2 font-medium text-slate-900">
                    {formatWhen(selectedAppointment.start)}
                  </p>
                  <p className="text-sm text-slate-600">{selectedAppointment.location_name}</p>
                </div>
                <div className="rounded-xl bg-teal-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-teal-700">New</p>
                  <p className="mt-2 font-medium text-slate-900">{formatWhen(pendingSlot.start)}</p>
                  <p className="text-sm text-slate-600">{pendingSlot.location_name}</p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl bg-teal-50 p-4">
                <p className="font-medium text-slate-900">{pendingSlot.service_name}</p>
                <p className="mt-1 text-sm text-slate-700">{formatWhen(pendingSlot.start)}</p>
                <p className="text-sm text-slate-600">{pendingSlot.location_name}</p>
                <p className="text-sm text-slate-600">{pendingSlot.practitioner_name}</p>
              </div>
            )}
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button variant="secondary" onClick={() => setPendingSlot(null)}>
                Keep looking
              </Button>
              <Button disabled={busy} onClick={() => void confirmPending()}>
                {busy
                  ? "Saving…"
                  : selectedAppointment
                    ? "Confirm reschedule"
                    : "Confirm booking"}
              </Button>
            </div>
          </div>
        ) : null}
      </Dialog>

      <Dialog
        open={Boolean(cancelTarget)}
        title="Cancel appointment?"
        onClose={() => setCancelTarget(null)}
      >
        {cancelTarget ? (
          <div className="space-y-4">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="font-medium text-slate-900">{cancelTarget.specialty}</p>
              <p className="text-sm text-slate-600">{cancelTarget.practitioner_name}</p>
              <p className="mt-2 text-sm text-slate-700">{formatWhen(cancelTarget.start)}</p>
              <p className="text-sm text-slate-500">{cancelTarget.location_name}</p>
            </div>
            <label className="block text-sm font-medium text-slate-700" htmlFor="cancel-reason">
              Cancellation reason (optional)
            </label>
            <textarea
              id="cancel-reason"
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
              rows={3}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-100"
            />
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button variant="secondary" onClick={() => setCancelTarget(null)}>
                Keep appointment
              </Button>
              <Button variant="danger" disabled={busy} onClick={() => void confirmCancel()}>
                {busy ? "Cancelling…" : "Cancel appointment"}
              </Button>
            </div>
          </div>
        ) : null}
      </Dialog>
    </section>
  );
}
