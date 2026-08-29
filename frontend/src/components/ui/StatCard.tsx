import type { ReactNode } from "react";

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

/**
 * A counter in the operations strip. No icon, no tinted square, no card —
 * a mono column label, the figure in its state colour, and a required
 * "so what" line, because every number here answers "what do I do".
 */
export function StatCard({
  label,
  value,
  hint,
  // Accent by default: an unremarkable figure is still the thing the reader
  // came for, so it carries the brand. An explicit tone always wins, so a
  // figure that means something states its own colour.
  tone = "accent",
  className,
}: {
  label: string;
  value: ReactNode;
  /** Required: what this number means for the reader. */
  hint: string;
  tone?: CounterTone;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-[5px] px-5 py-4", className)}>
      <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-[1.6875rem] leading-none tabular-nums",
          FIGURE_TONE[tone],
        )}
      >
        {value}
      </span>
      <span className="text-[12.5px] leading-snug text-secondary">{hint}</span>
    </div>
  );
}

/**
 * The counters read as one panel rather than four loose columns — a raised
 * surface under an accent cap, so the strip belongs to the section it opens.
 *
 * The dividers are grid gaps showing the strip's own background through, not a
 * border on each cell: callers set a different column count per breakpoint, and
 * a per-child `border-l` cannot know which cell starts a row — it drew a stray
 * rule down the left edge of the mobile stack and of every wrapped row. Gaps
 * separate neighbours only, at any column count, with no nth-child arithmetic.
 */
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
        "on-raised grid gap-px border-t-2 border-accent bg-rule [&>*]:bg-raised",
        className,
      )}
    >
      {children}
    </div>
  );
}
