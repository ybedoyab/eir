import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import Link from "next/link";

export function SectionHeader({
  title,
  description,
  actionHref,
  actionLabel,
  icon: Icon,
}: {
  title: string;
  description?: string;
  actionHref?: string;
  actionLabel?: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          {Icon ? <Icon aria-hidden className="h-4 w-4 text-teal-700" /> : null}
          {title}
        </h2>
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>
      {actionHref && actionLabel ? (
        <Link
          href={actionHref}
          className="text-sm font-medium text-teal-700 hover:text-teal-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function SectionHeaderAction({ children }: { children: ReactNode }) {
  return <div className="mb-4 flex justify-end">{children}</div>;
}
