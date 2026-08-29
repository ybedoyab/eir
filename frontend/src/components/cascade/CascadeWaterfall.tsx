"use client";

import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

export type CascadeKind = "agent" | "runtime" | "external" | "suppressed";

export interface CascadeStep {
  id: string;
  /** Event name, or `agent · capability`. */
  label: string;
  detail?: string;
  /** ISO timestamp from the event itself, never the fetch. */
  at: string;
  /** Known duration; otherwise the gap to the next step is used. */
  durationMs?: number;
  kind: CascadeKind;
  outcome?: string;
  outcomeTone?: "ok" | "warn" | "high" | "muted";
  /** True on the step where a blocking capability parked the workflow. */
  halted?: boolean;
}

const BAR: Record<CascadeKind, string> = {
  agent: "bg-accent",
  runtime: "bg-rule-strong",
  external: "border border-muted",
  suppressed: "border border-dashed border-rule-strong",
};

const OUTCOME: Record<NonNullable<CascadeStep["outcomeTone"]>, string> = {
  ok: "text-ok",
  warn: "text-warn",
  high: "text-high",
  muted: "text-muted",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(ms < 10_000 ? 2 : 1)}s`;
}

interface Placed extends CascadeStep {
  offsetMs: number;
  spanMs: number;
  indent: number;
}

/** Lays the run out against event timestamps — the poll boundary never shows. */
function place(steps: CascadeStep[]): { rows: Placed[]; totalMs: number } {
  const timed = steps.filter((step) => step.kind !== "suppressed");
  const times = timed.map((step) => new Date(step.at).getTime()).filter((n) => !Number.isNaN(n));
  const start = times.length ? Math.min(...times) : 0;
  const end = times.length ? Math.max(...times) : 0;

  const rows = steps.map((step, index) => {
    const at = new Date(step.at).getTime();
    const offsetMs = Number.isNaN(at) ? end - start : at - start;
    const nextTimed = steps
      .slice(index + 1)
      .find((item) => item.kind !== "suppressed" && !Number.isNaN(new Date(item.at).getTime()));
    const gap = nextTimed ? new Date(nextTimed.at).getTime() - at : 0;
    const spanMs = step.durationMs ?? Math.max(gap, 0);
    return { ...step, offsetMs, spanMs, indent: Math.min(index, 5) * 22 };
  });

  const totalMs = Math.max(
    rows.reduce((max, row) => Math.max(max, row.offsetMs + row.spanMs), 0),
    1,
  );
  return { rows, totalMs };
}

export function CascadeWaterfall({
  steps,
  selectedId,
  onSelect,
  className,
}: {
  steps: CascadeStep[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  className?: string;
}) {
  const { rows, totalMs } = place(steps);
  // One tick per second of the run, capped at 6. Each label is placed at its own
  // fraction of `totalMs` — evenly spaced flex children put "1s" wherever the
  // column happened to divide, so the ruler disagreed with the bars beneath it.
  const ticks = Math.max(1, Math.min(6, Math.ceil(totalMs / 1000)));

  return (
    <div className={cn("flex min-w-0 flex-col", className)}>
      <div className="flex flex-wrap items-center justify-end gap-4 pb-3 font-mono text-[10.5px] text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-3.5 bg-accent" aria-hidden />
          agent
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-3.5 bg-rule-strong" aria-hidden />
          runtime
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-3.5 border border-muted" aria-hidden />
          external
        </span>
      </div>

      {/* ruler */}
      <div className="grid grid-cols-[minmax(0,1fr)_78px] items-end gap-4 border-b border-rule-strong pb-1.5 sm:grid-cols-[280px_minmax(0,1fr)_78px]">
        <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">Step</span>
        <div className="relative hidden h-4 font-mono text-[0.75rem] text-muted sm:block">
          {Array.from({ length: ticks }, (_, index) => (
            <span
              key={index}
              className="absolute top-0"
              style={{ left: `${Math.min((index * 1000) / totalMs, 1) * 100}%` }}
            >
              {index}s
            </span>
          ))}
        </div>
        <span className="text-right font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
          Took
        </span>
      </div>

      {rows.map((row) => {
        const selected = row.id === selectedId;
        const suppressed = row.kind === "suppressed";
        const left = `${(row.offsetMs / totalMs) * 100}%`;
        const width = `${Math.max((row.spanMs / totalMs) * 100, 1.2)}%`;
        const Row = onSelect ? "button" : "div";
        return (
          <Row
            key={row.id}
            {...(onSelect
              ? { type: "button" as const, onClick: () => onSelect(row.id) }
              : {})}
            aria-current={selected ? "true" : undefined}
            className={cn(
              "focus-ink grid w-full grid-cols-[minmax(0,1fr)_78px] items-center gap-4 border-b border-rule text-left sm:grid-cols-[280px_minmax(0,1fr)_78px]",
              suppressed ? "min-h-10" : "min-h-[46px]",
              selected && "on-raised bg-raised shadow-[inset_3px_0_0_0_var(--color-accent)]",
              onSelect && !selected && "hover:bg-hover",
            )}
          >
            <div
              className="flex min-w-0 items-center gap-2.5 border-l border-hover"
              style={{ paddingLeft: row.indent + 10 }}
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span
                  className={cn(
                    "truncate font-mono text-[12.5px]",
                    suppressed ? "text-inactive line-through" : "text-ink",
                    selected && "font-medium",
                  )}
                >
                  {row.label}
                </span>
                {row.detail ? (
                  <span
                    className={cn(
                      "truncate font-mono text-[0.75rem]",
                      row.halted ? "text-high" : "text-muted",
                    )}
                  >
                    {row.detail}
                  </span>
                ) : null}
              </div>
            </div>

            <div className="relative hidden h-[26px] items-center sm:flex">
              <span
                aria-hidden
                className={cn("absolute h-2.5", BAR[row.kind])}
                style={{ left, width }}
              />
              {row.halted ? (
                <span
                  aria-hidden
                  className="absolute h-[26px] w-[3px] bg-ink"
                  style={{ left: `calc(${left} + ${width})` }}
                />
              ) : null}
            </div>

            <span
              className={cn(
                "text-right font-mono text-[11.5px]",
                suppressed
                  ? "text-inactive"
                  : row.outcomeTone
                    ? OUTCOME[row.outcomeTone]
                    : "text-secondary",
              )}
            >
              {suppressed ? "suppressed" : (row.outcome ?? formatDuration(row.spanMs))}
            </span>
          </Row>
        );
      })}
    </div>
  );
}

/** 0ms, no easing. Everything stops, hard. */
export function HaltBanner({
  title,
  detail,
  held,
  className,
}: {
  title: string;
  detail: string;
  held?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "eir-halt flex flex-col gap-2 border-l-[3px] border-high bg-ink px-[18px] py-4 sm:flex-row sm:items-center sm:gap-4",
        className,
      )}
    >
      <span className="inline-flex shrink-0 items-center gap-2 font-mono text-[0.75rem] font-medium tracking-[0.12em] text-paper">
        <Icon name="halt" size={14} />
        {title}
      </span>
      <span className="text-[0.8125rem] leading-snug text-on-ink">{detail}</span>
      {held ? (
        <span className="font-mono text-[0.75rem] text-on-ink-muted sm:ml-auto">held {held}</span>
      ) : null}
    </div>
  );
}
