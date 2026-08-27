import { cn } from "@/lib/cn";

function initialsFor(name: string): string {
  const cleaned = name.replace(/^Dr\.\s+/i, "").trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "E";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

const sizes = {
  sm: "h-8 w-8 text-[0.75rem]",
  md: "h-10 w-10 text-[0.75rem]",
  lg: "h-12 w-12 text-[0.8125rem]",
  xl: "h-14 w-14 text-[0.9375rem]",
};

/**
 * Square, neutral, mono. An identity marker is structure, not state, so it
 * never carries hue — and a hashed colour per name would be decoration.
 */
export function Avatar({
  name,
  size = "md",
  className,
}: {
  name: string;
  size?: keyof typeof sizes;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex shrink-0 items-center justify-center border border-rule bg-raised font-mono tracking-[0.06em] text-secondary",
        sizes[size],
        className,
      )}
    >
      {initialsFor(name)}
    </span>
  );
}
