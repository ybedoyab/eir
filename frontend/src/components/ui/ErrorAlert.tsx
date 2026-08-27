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
      className="on-raised mb-6 flex flex-col gap-3 border-l-[3px] border-high bg-raised px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="flex flex-col gap-1">
        <span className="font-mono text-[0.75rem] font-medium uppercase tracking-[0.08em] text-high">
          Failed
        </span>
        <span className="text-[13.5px] leading-snug text-secondary">{message}</span>
      </p>
      {onRetry ? (
        <Button variant="secondary" className="shrink-0" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
