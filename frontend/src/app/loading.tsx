import { RouteSkeleton } from "@/components/ui/RouteSkeleton";

/**
 * Fallback boundary for segments that have no role layout of their own
 * (`/`, `/login`, `/demo`, `/patients`, `/agents`). It supplies the page
 * padding those routes would otherwise inherit from a layout.
 */
export default function Loading() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col px-5 py-10 sm:px-8">
      <RouteSkeleton />
    </div>
  );
}
