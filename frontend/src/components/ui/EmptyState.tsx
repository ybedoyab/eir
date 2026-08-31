import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="eir-surface-soft on-raised px-6 py-9">
      <span className="eir-icon-shell mb-4 h-10 w-10" aria-hidden>
        <Icon name="sparkles" size={18} />
      </span>
      <p className="text-[0.9375rem] font-semibold text-ink">{title}</p>
      {description ? (
        <p className="mt-2 max-w-[56ch] text-[0.875rem] leading-relaxed text-secondary">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-5 flex">{action}</div> : null}
    </div>
  );
}
import { Icon } from "@/components/ui/Icon";
