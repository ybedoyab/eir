import { getHealth } from "@/services/api";

export async function ApiStatus() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const host = apiUrl.replace(/^https?:\/\//, "");

  try {
    const health = await getHealth();
    return (
      <div className="mx-auto flex max-w-6xl items-center gap-2.5 px-4 pb-3 pt-1 font-mono text-[11px] text-muted sm:px-6">
        <span className="inline-flex h-1.5 w-1.5 bg-ok" aria-hidden />
        <span>
          API <span className="text-ok">{health.status}</span>
        </span>
        <span className="hidden text-rule-strong sm:inline">·</span>
        <span className="truncate">{host}</span>
      </div>
    );
  } catch {
    return (
      <div className="mx-auto flex max-w-6xl items-center gap-2.5 px-4 pb-3 pt-1 font-mono text-[11px] text-muted sm:px-6">
        <span className="inline-flex h-1.5 w-1.5 bg-high" aria-hidden />
        <span className="font-medium text-high">API unreachable</span>
        <span className="hidden text-rule-strong sm:inline">·</span>
        <span className="truncate">{host}</span>
      </div>
    );
  }
}
