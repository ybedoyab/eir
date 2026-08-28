import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * A section, not a card. Square edges, no shadow, opened by the same 2px accent
 * cap a `SectionHeader level="major"` draws — a Card sits at that same rank,
 * so it must not read as a different kind of thing. Density comes from
 * removing chrome, never from shrinking targets.
 */
export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("flex flex-col border-t-2 border-accent pt-3.5", className)}>
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
      <div>
        <h2 className="font-mono text-[11.5px] font-semibold uppercase tracking-[0.12em] text-accent">
          {title}
        </h2>
        {description ? (
          <p className="mt-2 max-w-[68ch] text-[13.5px] leading-relaxed text-secondary normal-case tracking-normal">
            {description}
          </p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
