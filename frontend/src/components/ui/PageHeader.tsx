import type { ReactNode } from "react";

import { Icon, type IconName } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

type Density = "patient" | "staff" | "dense";

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

const DENSITY_ICON: Record<Density, IconName> = {
  patient: "heart",
  staff: "activity",
  dense: "overview",
};

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  density = "staff",
  icon,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  density?: Density;
  icon?: IconName;
}) {
  const resolvedIcon = icon ?? DENSITY_ICON[density];

  return (
    <div
      className={cn(
        "eir-enter flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between",
        GAP[density],
      )}
    >
      <div className="flex max-w-3xl items-start gap-4">
        <span className="eir-icon-shell eir-pop mt-0.5 h-11 w-11" aria-hidden>
          <Icon name={resolvedIcon} size={20} />
        </span>
        <div>
          {eyebrow ? (
            <span className="font-mono text-[10.5px] font-medium uppercase tracking-[0.12em] text-accent">
              {eyebrow}
            </span>
          ) : null}
          <h1 className={cn("mt-1.5 font-serif font-medium text-ink", TITLE[density])}>{title}</h1>
          {description ? (
            <p className={cn("text-secondary", DESCRIPTION[density])}>{description}</p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
