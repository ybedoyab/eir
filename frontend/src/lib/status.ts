import type { EpisodeStatus, RiskLevel } from "@/types";

/**
 * Chip classes for the places that render a status without going through
 * `StatusBadge`. Same progression: outline -> tint -> fill -> fill with an
 * ink halt rule. All six `EpisodeStatus` members are covered; `WAITING` and
 * `WAITING_FOR_NEXT_FOLLOWUP` take the neutral outline and `CANCELLED` the
 * inactive treatment.
 */
const episodeTone: Record<EpisodeStatus, string> = {
  ACTIVE: "border border-ok text-ok",
  WAITING: "border border-rule-strong text-secondary",
  WAITING_FOR_NEXT_FOLLOWUP: "border border-rule-strong text-secondary",
  ESCALATED: "bg-high font-medium text-paper",
  COMPLETED: "border border-rule text-muted",
  CANCELLED: "border border-rule text-muted",
};

/** LOW takes the NORMAL treatment, MEDIUM the ELEVATED treatment. */
const riskTone: Record<RiskLevel, string> = {
  LOW: "border border-rule-strong text-secondary",
  MEDIUM: "border border-warn bg-warn-tint text-warn",
  HIGH: "bg-high font-medium text-paper",
  CRITICAL: "border-l-[3px] border-ink bg-crit font-medium text-paper",
};

export function episodeBadgeClass(status: EpisodeStatus): string {
  return episodeTone[status];
}

export function riskBadgeClass(risk: RiskLevel): string {
  return riskTone[risk];
}
