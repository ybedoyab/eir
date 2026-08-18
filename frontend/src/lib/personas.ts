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

export function roleLabel(role: string): string {
  if (role === "PATIENT") return "Patient";
  if (role === "CLINICIAN") return "Clinician";
  if (role === "OPERATIONS_ADMIN") return "Administrator";
  return role;
}
