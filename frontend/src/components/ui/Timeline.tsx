import type { LucideIcon } from "lucide-react";
import { CalendarDays } from "lucide-react";

export function Timeline({
  items,
}: {
  items: Array<{
    id: string;
    title: string;
    detail?: string;
    at: string;
    icon?: LucideIcon;
  }>;
}) {
  if (!items.length) return null;
  return (
    <ol className="space-y-3">
      {items.map((item) => {
        const Icon = item.icon ?? CalendarDays;
        return (
          <li key={item.id} className="flex gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-50 text-teal-800">
              <Icon aria-hidden className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-medium text-slate-900">{item.title}</p>
              {item.detail ? <p className="text-sm text-slate-600">{item.detail}</p> : null}
              <p className="mt-0.5 text-xs text-slate-500">{item.at}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
