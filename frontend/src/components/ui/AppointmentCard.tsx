import { MapPin } from "lucide-react";
import type { ReactNode } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/cn";
import { formatDateShort, formatTime, specialtyIcon } from "@/lib/format";
import { appointmentStatus } from "@/lib/statusLabels";
import type { Appointment } from "@/lib/auth";

export function AppointmentCard({
  appointment,
  patientName,
  actions,
  className,
}: {
  appointment: Appointment;
  patientName?: string;
  actions?: ReactNode;
  className?: string;
}) {
  const Icon = specialtyIcon(appointment.specialty);
  const status = appointmentStatus(appointment.status);
  return (
    <article
      className={cn(
        "flex flex-col gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[var(--eir-shadow)] sm:flex-row sm:items-start sm:justify-between",
        className,
      )}
    >
      <div className="flex gap-4">
        <div className="flex h-[4.5rem] w-16 shrink-0 flex-col items-center justify-center rounded-xl bg-teal-50 text-teal-900">
          <span className="text-xs font-medium uppercase tracking-wide">
            {formatDateShort(appointment.start).split(" ")[0]}
          </span>
          <span className="text-lg font-semibold leading-tight">
            {new Date(appointment.start).getDate()}
          </span>
        </div>
        <div>
          <p className="flex items-center gap-2 text-base font-semibold text-slate-900">
            <Icon aria-hidden className="h-4 w-4 text-teal-700" />
            {appointment.specialty}
          </p>
          <div className="mt-1 flex items-center gap-2 text-sm text-slate-600">
            <Avatar name={patientName ?? appointment.practitioner_name} size="sm" />
            <span>{patientName ?? appointment.practitioner_name}</span>
          </div>
          <p className="mt-2 text-sm text-slate-700">{formatTime(appointment.start)}</p>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500">
            <MapPin aria-hidden className="h-3.5 w-3.5" />
            {appointment.location_name}
          </p>
          <div className="mt-3">
            <StatusBadge status={status} />
          </div>
        </div>
      </div>
      {actions ? <div className="flex flex-wrap gap-2 sm:justify-end">{actions}</div> : null}
    </article>
  );
}
