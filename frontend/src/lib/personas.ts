export interface DemoPersonaCopy {
  username: string;
  description: string;
  primary: boolean;
}

export const DEMO_PERSONAS: Record<string, DemoPersonaCopy> = {
  alex: {
    username: "alex",
    description: "Manage appointments and recovery",
    primary: true,
  },
  clinician: {
    username: "clinician",
    description: "Review patients and escalations",
    primary: true,
  },
  admin: {
    username: "admin",
    description: "Monitor hospital operations and agent fleet",
    primary: true,
  },
  jordan: {
    username: "jordan",
    description: "Alternate patient view",
    primary: false,
  },
};

const ROLE_LABELS: Record<DemoRole, string> = {
  PATIENT: "Patient",
  CLINICIAN: "Clinician",
  OPERATIONS_ADMIN: "Administrator",
};

export function roleLabel(role: string): string {
  return ROLE_LABELS[role as DemoRole] ?? role;
}
import type { DemoRole } from "@/lib/auth";
