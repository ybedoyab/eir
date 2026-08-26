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
    <div className="border-t border-rule px-0 py-10">
      <p className="text-[15px] font-medium text-ink">{title}</p>
      {description ? (
        <p className="mt-2 max-w-[56ch] text-[14px] leading-relaxed text-secondary">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-5 flex">{action}</div> : null}
    </div>
  );
}
