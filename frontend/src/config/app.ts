export const APP_META = {
  name: "EIR",
  title: "EIR — Healthcare Agent Fleet",
  description: "AI-powered hospital operations with secure multi-agent workflows.",
  longName: "Enterprise Intelligence Runtime",
  environmentNote: "Demo environment · no real patient data",
} as const;

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const APP_ROUTES = {
  home: "/",
  login: "/login",
  demo: "/demo",
  patients: "/patients",
  recovery: "/recovery",
  agents: "/agents",
  observability: "/observability",
  voicePreview: "/voice-preview",
  patient: {
    home: "/patient",
    appointments: "/patient/appointments",
    recovery: "/patient/recovery",
    assistant: "/patient/assistant",
  },
  clinician: {
    home: "/clinician",
    schedule: "/clinician/schedule",
    reviews: "/clinician/reviews",
    patients: "/clinician/patients",
  },
  admin: {
    home: "/admin",
    fleet: "/admin/fleet",
    observability: "/admin/observability",
    appointments: "/admin/appointments",
    patients: "/admin/patients",
    inventory: "/admin/inventory",
  },
} as const;

export const APP_ROUTE_BUILDERS = {
  clinicianPatient: (patientId: string) => `${APP_ROUTES.clinician.patients}/${patientId}`,
  patientAppointments: (action?: "schedule" | "reschedule") =>
    action ? `${APP_ROUTES.patient.appointments}?action=${action}` : APP_ROUTES.patient.appointments,
  recoveryDetails: (episodeId: string) => `${APP_ROUTES.recovery}/${episodeId}`,
} as const;

export const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
  headers: {
    contentType: "Content-Type",
    json: "application/json",
    authorization: "Authorization",
  },
  authScheme: "Bearer",
} as const;

export const API_ROUTES = {
  health: "/health",
  auth: {
    login: "/api/v1/auth/login",
    me: "/api/v1/auth/me",
    demoUsers: "/api/v1/auth/demo-users",
  },
  patients: "/api/v1/patients",
  appointments: "/api/v1/appointments",
  appointmentAvailability: "/api/v1/appointments/availability",
  accessSessions: "/api/v1/access/sessions",
  adminSnapshot: "/api/v1/admin/snapshot",
  recovery: "/api/v1/recovery",
  reviews: "/api/v1/reviews",
  agents: "/api/v1/agents",
  traces: "/api/v1/traces",
  runtimeStatus: "/api/v1/runtime/status",
  runtimeHistory: "/api/v1/runtime/history",
  demoBootstrap: "/api/v1/demo/bootstrap",
  demoContext: "/api/v1/demo/context",
  demoFollowUp: "/api/v1/demo/advance-follow-up",
  demoSignal: "/api/v1/demo/concerning-signal",
  demoMockCheckin: "/api/v1/demo/mock-checkin",
  demoVoiceRetry: "/api/v1/demo/retry-voice",
  promptInjection: "/api/v1/security/demo/prompt-injection",
  voiceWebSession: "/api/v1/voice/web-session",
  inventory: "/api/v1/inventory",
  lowStock: "/api/v1/inventory/low-stock",
  suppliers: "/api/v1/inventory/suppliers",
  supplyCases: "/api/v1/supply/cases",
  supplyApprovals: "/api/v1/supply/approvals",
} as const;

export const UI_TIMING = {
  toast: 4200,
  entranceStep: 70,
  statusPulse: 2200,
} as const;

export const STORAGE_KEYS = {
  session: "eir.demo.session",
} as const;

export const HTTP_STATUS = {
  unauthorized: 401,
  forbidden: 403,
} as const;
