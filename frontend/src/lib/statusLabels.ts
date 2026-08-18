import type { EpisodeStatus, RiskLevel } from "@/types";

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral" | "brand";

export interface StatusView {
  label: string;
  tone: StatusTone;
}

const APPOINTMENT_STATUS: Record<string, StatusView> = {
  booked: { label: "Confirmed", tone: "success" },
  proposed: { label: "Proposed", tone: "info" },
  pending: { label: "Pending", tone: "warning" },
  arrived: { label: "Arrived", tone: "brand" },
  fulfilled: { label: "Completed", tone: "neutral" },
  cancelled: { label: "Cancelled", tone: "neutral" },
  canceled: { label: "Cancelled", tone: "neutral" },
  noshow: { label: "No show", tone: "danger" },
};

const EPISODE_STATUS: Record<EpisodeStatus, StatusView> = {
  ACTIVE: { label: "Active", tone: "brand" },
  WAITING: { label: "Waiting", tone: "warning" },
  WAITING_FOR_NEXT_FOLLOWUP: { label: "Follow-up scheduled", tone: "info" },
  ESCALATED: { label: "Escalated", tone: "danger" },
  COMPLETED: { label: "Completed", tone: "success" },
  CANCELLED: { label: "Cancelled", tone: "neutral" },
};

const RISK_CLINICIAN: Record<RiskLevel, StatusView> = {
  LOW: { label: "Low risk", tone: "success" },
  MEDIUM: { label: "Medium risk", tone: "warning" },
  HIGH: { label: "High risk", tone: "danger" },
  CRITICAL: { label: "Critical", tone: "danger" },
};

const RISK_PATIENT: Record<RiskLevel, StatusView> = {
  LOW: { label: "On track", tone: "success" },
  MEDIUM: { label: "Checking in regularly", tone: "info" },
  HIGH: { label: "Care team reviewing", tone: "warning" },
  CRITICAL: { label: "Care team reviewing", tone: "warning" },
};

export function appointmentStatus(status: string): StatusView {
  return APPOINTMENT_STATUS[status.toLowerCase()] ?? { label: status, tone: "neutral" };
}

export function episodeStatus(status: EpisodeStatus): StatusView {
  return EPISODE_STATUS[status];
}

export function riskStatus(risk: RiskLevel, audience: "patient" | "clinician" = "clinician"): StatusView {
  return audience === "patient" ? RISK_PATIENT[risk] : RISK_CLINICIAN[risk];
}

export function platformStatus(ok: boolean | null | undefined, liveLabel = "Live"): StatusView {
  if (ok === true) return { label: liveLabel, tone: "success" };
  if (ok === false) return { label: "Unverified", tone: "warning" };
  return { label: "Unknown", tone: "neutral" };
}
