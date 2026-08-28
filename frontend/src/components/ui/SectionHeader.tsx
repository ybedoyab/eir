import type { ReactNode } from "react";
import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

/**
 * Two ranks, so a page reads as a stack of blocks rather than one column of
 * hairlines. Mono, uppercase, letterspaced — this is the only place that
 * treatment is allowed, and it is never coloured.
 *
 * `major` opens a top-level section with a 2px ink cap rule above the label:
 * heavier than any rule inside a section, so the eye finds the boundaries
 * without a card, a shadow or a tint.
 *
 * `sub` (default) labels a block *inside* a major section — a hairline under
 * the label, one step down in size and contrast. Rank is carried by the rule
 * weight and the ink, never by colour.
 */
type Level = "major" | "sub";

// Three rule weights, so the eye can rank a line without reading it:
// 2px accent (section opens) > 2px rule-strong (block opens) > 1px rule (list row).
// A 1px sub rule was indistinguishable from the rows underneath it.
//
// The major rule and its label are the accent, not ink: repeated down every
// page they are what threads the brand blue through the composition, and they
// are structural — so they never collide with a status colour.
const WRAPPER: Record<Level, string> = {
  major: "mb-6 border-t-2 border-accent pt-3.5",
  sub: "mb-5 border-b-2 border-rule-strong pb-2.5",
};

const LABEL: Record<Level, string> = {
  major: "text-[11.5px] font-semibold tracking-[0.12em] text-accent",
  sub: "text-[11px] font-medium tracking-[0.1em] text-secondary",
};

export function SectionHeader({
  title,
  description,
  meta,
  actionHref,
  actionLabel,
  action,
  level = "sub",
  className,
}: {
  title: string;
  description?: string;
  /** Right-hand annotation, e.g. "first match by registration order". */
  meta?: string;
  actionHref?: string;
  actionLabel?: string;
  /** An arbitrary right-hand control. Wins over `actionHref` and `meta`. */
  action?: ReactNode;
  level?: Level;
  className?: string;
}) {
  // A major header opens the section, so it is the section's h2 and every
  // block inside it drops to h3. The outline follows the rules on the page.
  const Heading = level === "major" ? "h2" : "h3";

  return (
    <div className={cn("flex flex-col gap-2", WRAPPER[level], className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <Heading className={cn("font-mono uppercase", LABEL[level])}>{title}</Heading>
        {action ? (
          action
        ) : actionHref && actionLabel ? (
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
        <p className="max-w-[68ch] text-[13.5px] leading-relaxed text-secondary">{description}</p>
      ) : null}
    </div>
  );
}

export function SectionHeaderAction({ children }: { children: ReactNode }) {
  return <div className="mb-4 flex justify-end">{children}</div>;
}
