import { Skeleton } from "@/components/ui/Skeleton";

/**
 * The frame a route paints while its chunks and data are still in flight.
 *
 * Every page in the app is a client component that fetches in `useEffect`, so
 * without a `loading.tsx` boundary the App Router holds the *previous* page on
 * screen until the new segment's payload and JS have both landed — a click
 * that visibly does nothing. This is what the boundary shows instead.
 */
export function RouteSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-8" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading page</span>

      <div className="flex flex-col gap-3">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-9 w-[min(420px,70%)]" />
        <Skeleton className="h-4 w-[min(560px,90%)]" />
      </div>

      <div className="flex flex-col border-t border-rule-strong pt-4">
        {Array.from({ length: rows }, (_, index) => (
          <div
            key={index}
            className="grid grid-cols-[108px_minmax(0,1fr)_auto] items-center gap-5 border-b border-rule py-[18px]"
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
