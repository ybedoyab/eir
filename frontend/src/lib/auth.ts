import { APP_ROUTES, STORAGE_KEYS } from "@/config/app";

export type DemoRole = "PATIENT" | "CLINICIAN" | "OPERATIONS_ADMIN";

export interface AuthSession {
  token: string;
  role: DemoRole;
  display_name: string;
  patient_id?: string | null;
}

export interface Appointment {
  id: string;
  patient_id: string;
  status: string;
  specialty: string;
  service_name: string;
  practitioner_name: string;
  location_name: string;
  start: string;
  end: string;
  slot_id?: string | null;
  appointment_type: string;
  cancellation_reason?: string;
}

export interface SlotOption {
  id: string;
  specialty: string;
  service_name: string;
  practitioner_name: string;
  location_name: string;
  start: string;
  end: string;
}

export interface AccessSession {
  id: string;
  patient_id?: string | null;
  channel: string;
  status: string;
  current_intent: string;
  handoff_required: boolean;
  metadata: Record<string, unknown>;
}

export interface AccessMessageResponse {
  reply: string;
  session: AccessSession;
  appointments?: Appointment[];
  slots?: SlotOption[];
  appointment?: Appointment;
  handoff_required?: boolean;
  route?: string;
  capability?: string;
}

export interface AdminSnapshot {
  appointments: Record<string, number>;
  active_recoveries: number;
  pending_reviews: number;
  waitlist_requests?: number;
  low_stock_skus?: number;
  open_replenishments?: number;
  pending_purchase_approvals?: number;
}

const ROLE_HOME: Record<DemoRole, string> = {
  PATIENT: APP_ROUTES.patient.home,
  CLINICIAN: APP_ROUTES.clinician.home,
  OPERATIONS_ADMIN: APP_ROUTES.admin.home,
};

export function loadSession(): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(STORAGE_KEYS.session);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

export function saveSession(session: AuthSession): void {
  window.localStorage.setItem(STORAGE_KEYS.session, JSON.stringify(session));
}

export function clearSession(): void {
  window.localStorage.removeItem(STORAGE_KEYS.session);
}

export function roleHome(role: DemoRole): string {
  return ROLE_HOME[role];
}
