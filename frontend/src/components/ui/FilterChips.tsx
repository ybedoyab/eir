import { cn } from "@/lib/cn";

export function FilterChips<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: Array<{ id: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((option) => {
        const selected = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(option.id)}
            className={cn(
              "inline-flex min-h-11 items-center rounded-full px-3.5 text-sm font-medium ring-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600",
              selected
                ? "bg-teal-700 text-white ring-teal-700"
                : "bg-white text-slate-600 ring-slate-200 hover:bg-slate-50",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
