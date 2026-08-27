import type { ReactNode } from "react";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/cn";
import { formatDateShort, formatTime } from "@/lib/format";
import { appointmentStatus } from "@/lib/statusLabels";
import type { Appointment } from "@/lib/auth";

/**
 * An appointment row, not a card: date column, what and where, status,
 * action. Hairline rule underneath, square edges, no shadow.
 */
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
  const status = appointmentStatus(appointment.status);
  return (
    <article
      className={cn(
        "grid grid-cols-1 items-center gap-4 border-b border-rule py-6 sm:grid-cols-[132px_minmax(0,1fr)_auto] sm:gap-6",
        className,
      )}
    >
      <div className="flex flex-col gap-0.5">
        <span className="text-[1.25rem] font-semibold leading-tight text-ink">
          {formatDateShort(appointment.start)}
        </span>
        <span className="font-mono text-[0.8125rem] text-secondary">
          {formatTime(appointment.start)}
        </span>
      </div>

      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-[1.0625rem] font-medium text-ink">{appointment.specialty}</span>
        <span className="text-[0.875rem] text-secondary">
          {patientName ?? appointment.practitioner_name} · {appointment.location_name}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-3 sm:justify-end">
        <StatusBadge status={status} />
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </article>
  );
}
