import { cn } from "@/lib/cn";
import type { StatusTone, StatusView } from "@/lib/statusLabels";

/**
 * Severity climbs in visual weight, not just hue:
 * outline -> tint -> fill -> fill with an ink halt rule.
 * No icons. The word carries the meaning; a glyph would only compete.
 */
const TONE_CLASS: Record<StatusTone, string> = {
  neutral: "border border-rule-strong text-secondary",
  inactive: "border border-rule text-muted",
  info: "border border-rule-strong text-secondary",
  brand: "border border-accent text-accent",
  success: "border border-ok text-ok",
  warning: "border border-warn bg-warn-tint text-warn",
  danger: "bg-high font-medium text-paper",
  critical: "border-l-[3px] border-ink bg-crit font-medium text-paper",
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
        "eir-state inline-flex h-[26px] w-fit items-center px-2.5 font-mono text-[11.5px] uppercase leading-none tracking-[0.06em]",
        TONE_CLASS[status.tone],
        className,
      )}
    >
      {status.label}
    </span>
  );
}
