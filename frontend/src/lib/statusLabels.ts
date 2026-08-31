import type {
  EpisodeStatus,
  PurchaseOrderStatus,
  ReplenishmentStatus,
  RiskLevel,
  StockStatus,
  SupplyUrgency,
} from "@/types";

/**
 * Tones are visual weights, not colours picked per label. Severity climbs
 * outline -> tint -> fill -> fill with an ink halt rule; everything that is
 * not communicating state stays on the neutral ramp.
 */
export type StatusTone =
  | "success"
  | "warning"
  | "danger"
  | "critical"
  | "info"
  | "neutral"
  | "brand"
  | "inactive";

export interface StatusView {
  label: string;
  tone: StatusTone;
}

export const STATUS_VIEWS = {
  criticalMedication: { label: "Critical", tone: "critical" },
  noPendingReview: { label: "No pending review", tone: "success" },
  reviewNeeded: { label: "Review needed", tone: "danger" },
  securityBlocked: { label: "Security block recorded", tone: "critical" },
  waitingReview: { label: "Waiting review", tone: "warning" },
} as const satisfies Record<string, StatusView>;

const APPOINTMENT_STATUS: Record<string, StatusView> = {
  booked: { label: "Confirmed", tone: "success" },
  proposed: { label: "Proposed", tone: "info" },
  pending: { label: "Pending", tone: "warning" },
  arrived: { label: "Arrived", tone: "brand" },
  fulfilled: { label: "Completed", tone: "inactive" },
  cancelled: { label: "Cancelled", tone: "inactive" },
  canceled: { label: "Cancelled", tone: "inactive" },
  noshow: { label: "No show", tone: "danger" },
};

const EPISODE_STATUS: Record<EpisodeStatus, StatusView> = {
  ACTIVE: { label: "Active", tone: "success" },
  WAITING: { label: "Waiting", tone: "neutral" },
  WAITING_FOR_NEXT_FOLLOWUP: { label: "Follow-up due", tone: "neutral" },
  ESCALATED: { label: "Escalated", tone: "danger" },
  COMPLETED: { label: "Completed", tone: "inactive" },
  CANCELLED: { label: "Cancelled", tone: "inactive" },
};

const RISK_CLINICIAN: Record<RiskLevel, StatusView> = {
  LOW: { label: "Low", tone: "neutral" },
  MEDIUM: { label: "Medium", tone: "warning" },
  HIGH: { label: "High", tone: "danger" },
  CRITICAL: { label: "Critical", tone: "critical" },
};

const RISK_PATIENT: Record<RiskLevel, StatusView> = {
  LOW: { label: "On track", tone: "success" },
  MEDIUM: { label: "Checking in often", tone: "neutral" },
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
  // A fallback adapter is amber, never hidden and never green.
  if (ok === false) return { label: "Fallback", tone: "warning" };
  return { label: "Unknown", tone: "neutral" };
}

const STOCK_STATUS: Record<StockStatus, StatusView> = {
  HEALTHY: { label: "In stock", tone: "success" },
  LOW: { label: "Low stock", tone: "warning" },
  CRITICAL: { label: "Critically low", tone: "danger" },
  OUT_OF_STOCK: { label: "Out of stock", tone: "critical" },
};

const REPLENISHMENT_STATUS: Record<ReplenishmentStatus, StatusView> = {
  ACTIVE: { label: "Opened", tone: "brand" },
  SOURCING: { label: "Sourcing", tone: "info" },
  AWAITING_APPROVAL: { label: "Awaiting authorization", tone: "warning" },
  BLOCKED: { label: "Needs a buyer", tone: "danger" },
  ORDERED: { label: "Ordered", tone: "brand" },
  COMPLETED: { label: "Delivered", tone: "success" },
  CANCELLED: { label: "Cancelled", tone: "inactive" },
};

const SUPPLY_URGENCY: Record<SupplyUrgency, StatusView> = {
  NORMAL: { label: "Routine", tone: "neutral" },
  HIGH: { label: "Urgent", tone: "warning" },
  CRITICAL: { label: "Critical medication", tone: "critical" },
};

const PURCHASE_ORDER_STATUS: Record<PurchaseOrderStatus, StatusView> = {
  DRAFT: { label: "Draft", tone: "neutral" },
  APPROVED: { label: "Approved", tone: "brand" },
  PLACED: { label: "Placed", tone: "brand" },
  RECEIVED: { label: "Received", tone: "success" },
  CANCELLED: { label: "Cancelled", tone: "inactive" },
};

export function stockStatus(status: StockStatus): StatusView {
  return STOCK_STATUS[status] ?? { label: status, tone: "neutral" };
}

export function replenishmentStatus(status: ReplenishmentStatus): StatusView {
  return REPLENISHMENT_STATUS[status] ?? { label: status, tone: "neutral" };
}

export function supplyUrgency(urgency: SupplyUrgency): StatusView {
  return SUPPLY_URGENCY[urgency] ?? { label: urgency, tone: "neutral" };
}

export function purchaseOrderStatus(status: PurchaseOrderStatus): StatusView {
  return PURCHASE_ORDER_STATUS[status] ?? { label: status, tone: "neutral" };
}
