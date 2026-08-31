import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("eir-surface flex flex-col overflow-hidden p-5 sm:p-6", className)}>
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
    <div className="mb-6 flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-rule/80 pb-4">
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
