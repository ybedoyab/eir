import { cn } from "@/lib/cn";

const TONES = [
  "bg-teal-700",
  "bg-sky-800",
  "bg-slate-700",
  "bg-cyan-800",
  "bg-indigo-800",
  "bg-emerald-800",
];

function initialsFor(name: string): string {
  const cleaned = name.replace(/^Dr\.\s+/i, "").trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "E";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function toneFor(name: string): string {
  let hash = 0;
  for (const char of name) hash = (hash + char.charCodeAt(0)) % TONES.length;
  return TONES[hash] ?? TONES[0];
}

const sizes = {
  sm: "h-8 w-8 text-[11px]",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
  xl: "h-14 w-14 text-lg",
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
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white",
        toneFor(name),
        sizes[size],
        className,
      )}
    >
      {initialsFor(name)}
    </span>
  );
}
