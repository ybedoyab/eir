import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Density = "patient" | "staff" | "dense";

/** Row heights and type sizes per surface, from the density table. */
const TITLE: Record<Density, string> = {
  patient: "text-[2.5rem] leading-[1.15] tracking-[-0.018em]",
  staff: "text-[1.875rem] leading-[1.2] tracking-[-0.015em]",
  dense: "text-[1.6875rem] leading-[1.2] tracking-[-0.015em]",
};

const DESCRIPTION: Record<Density, string> = {
  patient: "mt-3 text-[1.0625rem] leading-[1.6]",
  staff: "mt-2 text-[14.5px] leading-[1.55]",
  dense: "mt-1.5 text-[13.5px] leading-[1.5]",
};

const GAP: Record<Density, string> = {
  patient: "mb-10",
  staff: "mb-7",
  dense: "mb-6",
};

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  density = "staff",
}: {
  /** A mono column label in the neutral ramp — never a coloured eyebrow. */
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  density?: Density;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between",
        GAP[density],
      )}
    >
      <div className="max-w-2xl">
        {eyebrow ? (
          <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            {eyebrow}
          </span>
        ) : null}
        <h1 className={cn("mt-2 font-serif font-medium text-ink", TITLE[density])}>{title}</h1>
        {description ? (
          <p className={cn("text-secondary", DESCRIPTION[density])}>{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
