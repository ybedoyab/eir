import { cn } from "@/lib/cn";
import type { StatusTone, StatusView } from "@/lib/statusLabels";

const TONE_CLASS: Record<StatusTone, string> = {
  neutral: "border border-rule-strong bg-surface/60 text-secondary",
  inactive: "border border-rule bg-raised text-muted",
  info: "border border-rule-strong bg-surface/60 text-secondary",
  brand: "border border-accent/35 bg-accent-tint text-accent",
  success: "border border-ok/30 bg-ok-tint text-ok",
  warning: "border border-warn/35 bg-warn-tint text-warn",
  danger: "bg-high font-medium text-paper",
  critical: "bg-crit font-medium text-paper shadow-[0_5px_14px_rgb(140_28_16/0.2)]",
};

export function StatusBadge({
  status,
  className,
}: {
  status: StatusView;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "eir-chip eir-state inline-flex h-[26px] w-fit items-center px-2.5 font-mono text-[11.5px] uppercase leading-none tracking-[0.06em]",
        TONE_CLASS[status.tone],
        className,
      )}
    >
      {status.label}
    </span>
  );
}
