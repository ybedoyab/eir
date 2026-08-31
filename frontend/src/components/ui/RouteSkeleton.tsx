import { Skeleton } from "@/components/ui/Skeleton";

export function RouteSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-8" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading page</span>

      <div className="flex flex-col gap-3">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-9 w-[min(420px,70%)]" />
        <Skeleton className="h-4 w-[min(560px,90%)]" />
      </div>

      <div className="eir-surface flex flex-col px-5 sm:px-6">
        {Array.from({ length: rows }, (_, index) => (
          <div
            key={index}
            className="grid grid-cols-[108px_minmax(0,1fr)_auto] items-center gap-5 border-b border-rule py-[18px] last:border-0"
          >
            <Skeleton className="h-3 w-16" />
            <Skeleton className={index % 3 === 2 ? "h-4 w-2/3" : "h-4 w-full"} />
            <Skeleton className="h-5 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}
