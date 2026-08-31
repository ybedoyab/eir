import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

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
      className="eir-enter mb-6 flex flex-col gap-4 rounded-xl border border-high/25 bg-high-tint px-4 py-3.5 shadow-[0_8px_24px_rgb(178_58_34/0.08)] sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-3">
        <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-high text-paper" aria-hidden>
          <Icon name="alertCircle" size={17} />
        </span>
        <p className="flex flex-col gap-1">
          <span className="font-mono text-[0.75rem] font-medium uppercase tracking-[0.08em] text-high">
            Request failed
          </span>
          <span className="text-[13.5px] leading-snug text-secondary">{message}</span>
        </p>
      </div>
      {onRetry ? (
        <Button variant="secondary" className="shrink-0" onClick={onRetry}>
          <Icon name="refresh" size={15} />
          Try again
        </Button>
      ) : null}
    </div>
  );
}
