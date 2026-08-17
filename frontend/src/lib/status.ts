import type { EpisodeStatus, RiskLevel } from "@/types";

const episodeTone: Record<EpisodeStatus, string> = {
  ACTIVE: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  WAITING: "bg-amber-50 text-amber-700 ring-amber-200",
  WAITING_FOR_NEXT_FOLLOWUP: "bg-sky-50 text-sky-700 ring-sky-200",
  ESCALATED: "bg-rose-50 text-rose-700 ring-rose-200",
  COMPLETED: "bg-slate-100 text-slate-700 ring-slate-200",
  CANCELLED: "bg-slate-100 text-slate-500 ring-slate-200",
};

const riskTone: Record<RiskLevel, string> = {
  LOW: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  MEDIUM: "bg-amber-50 text-amber-700 ring-amber-200",
  HIGH: "bg-orange-50 text-orange-700 ring-orange-200",
  CRITICAL: "bg-rose-50 text-rose-700 ring-rose-200",
};

export function episodeBadgeClass(status: EpisodeStatus): string {
  return episodeTone[status];
}

export function riskBadgeClass(risk: RiskLevel): string {
  return riskTone[risk];
}
