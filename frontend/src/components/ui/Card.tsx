import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * A section, not a card. Square edges, no shadow, delimited by a hairline
 * rule. Density comes from removing chrome, never from shrinking targets.
 */
export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("flex flex-col border-t border-rule-strong pt-4", className)}>
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
    <div className="mb-4 flex items-baseline justify-between gap-4 border-b border-rule pb-2.5">
      <div>
        <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
          {title}
        </h2>
        {description ? (
          <p className="mt-2 text-[13.5px] leading-relaxed text-secondary normal-case tracking-normal">
            {description}
          </p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
