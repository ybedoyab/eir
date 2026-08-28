import { Icon } from "@/components/ui/Icon";
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
              "focus-ink inline-flex min-h-11 items-center gap-2 px-4 text-sm",
              selected
                ? // Filled, not outlined: a selected filter is a live constraint
                  // on what you are looking at, so it should be the loudest
                  // thing in the row.
                  "on-accent border border-accent bg-accent font-medium text-paper"
                : "border border-rule text-secondary hover:bg-hover hover:text-ink",
            )}
          >
            {selected ? <Icon name="approve" size={14} className="text-paper" /> : null}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
