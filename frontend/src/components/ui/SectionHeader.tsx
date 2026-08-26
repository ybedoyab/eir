import type { ReactNode } from "react";
import Link from "next/link";

import { Icon } from "@/components/ui/Icon";

/**
 * A section label with its rule. Mono, uppercase, letterspaced — this is
 * the only place that treatment is allowed, and it is never coloured.
 */
export function SectionHeader({
  title,
  description,
  meta,
  actionHref,
  actionLabel,
}: {
  title: string;
  description?: string;
  /** Right-hand annotation, e.g. "first match by registration order". */
  meta?: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <div className="mb-4 flex flex-col gap-2 border-b border-rule-strong pb-2.5">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
          {title}
        </h2>
        {actionHref && actionLabel ? (
          <Link
            href={actionHref}
            className="focus-ink -my-3 inline-flex min-h-11 items-center gap-1.5 text-sm text-accent hover:text-ink"
          >
            {actionLabel}
            <Icon name="chevronRight" size={14} />
          </Link>
        ) : meta ? (
          <span className="font-mono text-[10.5px] text-muted">{meta}</span>
        ) : null}
      </div>
      {description ? (
        <p className="text-[13.5px] leading-relaxed text-secondary">{description}</p>
      ) : null}
    </div>
  );
}

export function SectionHeaderAction({ children }: { children: ReactNode }) {
  return <div className="mb-4 flex justify-end">{children}</div>;
}
