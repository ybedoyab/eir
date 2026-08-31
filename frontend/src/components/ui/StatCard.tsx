import type { ReactNode } from "react";

import { Icon, type IconName } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

export type CounterTone = "ink" | "accent" | "ok" | "warn" | "high" | "crit";

const FIGURE_TONE: Record<CounterTone, string> = {
  ink: "text-ink",
  accent: "text-accent",
  ok: "text-ok",
  warn: "text-warn",
  high: "text-high",
  crit: "text-crit",
};

const FIGURE_ICON: Record<CounterTone, IconName> = {
  ink: "activity",
  accent: "sparkles",
  ok: "checkCircle",
  warn: "clock",
  high: "alertCircle",
  crit: "bell",
};

export function StatCard({
  label,
  value,
  hint,
  tone = "accent",
  icon,
  className,
}: {
  label: string;
  value: ReactNode;
  hint: string;
  tone?: CounterTone;
  icon?: IconName;
  className?: string;
}) {
  return (
    <div className={cn("group flex flex-col gap-[5px] px-5 py-5", className)}>
      <span className="flex items-center justify-between gap-3">
        <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
          {label}
        </span>
        <span className="eir-icon-shell h-8 w-8 rounded-lg" aria-hidden>
          <Icon name={icon ?? FIGURE_ICON[tone]} size={15} />
        </span>
      </span>
      <span
        className={cn(
        "mt-1 font-mono text-[1.875rem] font-medium leading-none tabular-nums",
          FIGURE_TONE[tone],
        )}
      >
        {value}
      </span>
      <span className="text-[12.5px] leading-snug text-secondary">{hint}</span>
    </div>
  );
}

export function StatStrip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "eir-surface eir-stagger on-surface grid overflow-hidden bg-rule/70 [&>*]:bg-surface/95",
        className,
      )}
    >
      {children}
    </div>
  );
}
