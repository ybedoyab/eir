import type { ReactNode } from "react";
import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

type Level = "major" | "sub";

const WRAPPER: Record<Level, string> = {
  major: "mb-6 border-b border-rule/80 pb-3.5",
  sub: "mb-5 border-b border-rule/70 pb-2.5",
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
  meta?: string;
  actionHref?: string;
  actionLabel?: string;
  action?: ReactNode;
  level?: Level;
  className?: string;
}) {
  const Heading = level === "major" ? "h2" : "h3";

  return (
    <div className={cn("flex flex-col gap-2", WRAPPER[level], className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <span className="flex items-center gap-2.5">
          <span className={cn("h-1.5 rounded-full bg-accent", level === "major" ? "w-6" : "w-3")} aria-hidden />
          <Heading className={cn("font-mono uppercase", LABEL[level])}>{title}</Heading>
        </span>
        {action ? (
          action
        ) : actionHref && actionLabel ? (
          <Link
            href={actionHref}
            className="focus-ink group -my-3 inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 text-sm font-medium text-accent hover:bg-accent-tint hover:text-ink"
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
