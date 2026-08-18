import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";
import type { StatusTone, StatusView } from "@/lib/statusLabels";

const TONE_CLASS: Record<StatusTone, string> = {
  success: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  warning: "bg-amber-50 text-amber-800 ring-amber-200",
  danger: "bg-rose-50 text-rose-800 ring-rose-200",
  info: "bg-sky-50 text-sky-800 ring-sky-200",
  brand: "bg-teal-50 text-teal-800 ring-teal-200",
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
};

const TONE_ICON: Record<StatusTone, LucideIcon> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  info: Clock,
  brand: ShieldCheck,
  neutral: Clock,
};

export function StatusBadge({
  status,
  className,
}: {
  status: StatusView;
  className?: string;
}) {
  const Icon = TONE_ICON[status.tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        TONE_CLASS[status.tone],
        className,
      )}
    >
      <Icon aria-hidden className="h-3.5 w-3.5" />
      {status.label}
    </span>
  );
}
