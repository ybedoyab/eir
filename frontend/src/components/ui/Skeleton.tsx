import { cn } from "@/lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("animate-pulse rounded-xl bg-slate-200/80", className)}
    />
  );
}

export function SkeletonLines({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className={index === rows - 1 ? "h-4 w-2/3" : "h-4 w-full"} />
      ))}
    </div>
  );
}

export function CardSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[var(--eir-shadow)]">
      <Skeleton className="mb-4 h-5 w-40" />
      <SkeletonLines rows={rows} />
    </div>
  );
}
