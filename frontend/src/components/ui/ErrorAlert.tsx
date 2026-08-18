import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/Button";

export function ErrorAlert({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="mb-6 flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="flex items-start gap-2">
        <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{message}</span>
      </p>
      {onRetry ? (
        <Button variant="secondary" className="shrink-0" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
