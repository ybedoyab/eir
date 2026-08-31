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
        "inline-flex shrink-0 items-center justify-center rounded-full border border-accent/20 bg-gradient-to-br from-surface via-accent-tint to-sky font-mono font-semibold tracking-[0.06em] text-accent shadow-[0_6px_18px_rgb(22_75_130/0.12)]",
        sizes[size],
        className,
      )}
    >
      {initialsFor(name)}
    </span>
  );
}
