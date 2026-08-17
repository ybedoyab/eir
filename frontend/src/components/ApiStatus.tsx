import { getHealth } from "@/services/api";

export async function ApiStatus() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const host = apiUrl.replace(/^https?:\/\//, "");

  try {
    const health = await getHealth();
    return (
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 pb-3 pt-1 text-xs text-slate-500 sm:px-6">
        <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" aria-hidden />
        <span>
          API <span className="font-medium text-slate-700">{health.status}</span>
        </span>
        <span className="hidden text-slate-400 sm:inline">·</span>
        <span className="truncate font-mono text-[11px] text-slate-400">{host}</span>
      </div>
    );
  } catch {
    return (
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 pb-3 pt-1 text-xs text-rose-700 sm:px-6">
        <span className="inline-flex h-2 w-2 rounded-full bg-rose-500" aria-hidden />
        <span className="font-medium">API unreachable</span>
        <span className="truncate font-mono text-[11px] text-rose-500">{host}</span>
      </div>
    );
  }
}
