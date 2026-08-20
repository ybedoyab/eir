import { loadSession } from "@/lib/auth";
import type {
  AccessMessageResponse,
  AccessSession,
  AdminSnapshot,
  Appointment,
  AuthSession,
  SlotOption,
} from "@/lib/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function authHeaders(): Record<string, string> {
  const session = typeof window !== "undefined" ? loadSession() : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (session?.token) {
    headers.Authorization = `Bearer ${session.token}`;
  }
  return headers;
}

async function getJson<T>(path: string, authenticated = false): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: authenticated ? authHeaders() : undefined,
  });
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json();
}

async function postJson<T>(path: string, body: unknown, authenticated = false): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: authenticated ? authHeaders() : { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json();
}

export async function getHealth(): Promise<{ status: string }> {
  return getJson("/health");
}

export async function loginDemo(username: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error("Login failed");
  }
  const body = await response.json();
  return {
    token: body.token,
    role: body.role,
    display_name: body.display_name,
    patient_id: body.patient_id,
  };
}

export async function listDemoUsers() {
  return getJson<
    Array<{
      username: string;
      display_name: string;
      role: string;
      password_hint: string;
    }>
  >("/api/v1/auth/demo-users");
}

export async function listPatients() {
  return getJson<import("@/types").Patient[]>("/api/v1/patients");
}

export async function getPatient(id: string) {
  return getJson<import("@/types").Patient>(`/api/v1/patients/${id}`);
}

export async function listAppointments() {
  return getJson<Appointment[]>("/api/v1/appointments", true);
}

export async function searchAvailability(params: {
  specialty?: string;
  time_of_day?: string;
  location_id?: string;
}) {
  const query = new URLSearchParams();
  if (params.specialty) query.set("specialty", params.specialty);
  if (params.time_of_day) query.set("time_of_day", params.time_of_day);
  if (params.location_id) query.set("location_id", params.location_id);
  return getJson<SlotOption[]>(`/api/v1/appointments/availability?${query.toString()}`, true);
}

export async function bookAppointment(slotId: string) {
  return postJson<Appointment>("/api/v1/appointments", { slot_id: slotId }, true);
}

export async function rescheduleAppointment(appointmentId: string, slotId: string) {
  return postJson<Appointment>(
    `/api/v1/appointments/${appointmentId}/reschedule`,
    { slot_id: slotId },
    true,
  );
}

export async function cancelAppointment(appointmentId: string, reason: string) {
  return postJson<Appointment>(
    `/api/v1/appointments/${appointmentId}/cancel`,
    { confirmed: true, reason },
    true,
  );
}

export async function createAccessSession() {
  return postJson<AccessSession>("/api/v1/access/sessions", { channel: "web" }, true);
}

export async function sendAccessMessage(sessionId: string, message: string) {
  return postJson<AccessMessageResponse>(
    `/api/v1/access/sessions/${sessionId}/message`,
    { message },
    true,
  );
}

export async function getAdminSnapshot() {
  return getJson<AdminSnapshot>("/api/v1/admin/snapshot", true);
}

export async function listRecovery() {
  return getJson<import("@/types").RecoveryEpisode[]>("/api/v1/recovery");
}

export async function getRecovery(id: string) {
  return getJson<import("@/types").RecoveryEpisode>(`/api/v1/recovery/${id}`);
}

export async function listRecoveryEvents(id: string) {
  return getJson<import("@/types").DomainEvent[]>(`/api/v1/recovery/${id}/events`);
}

export async function createRecovery(patientId: string) {
  return postJson<import("@/types").RecoveryEpisode>("/api/v1/recovery", {
    patient_id: patientId,
  });
}

export async function triggerFollowUp(episodeId: string) {
  return postJson<{ episode: import("@/types").RecoveryEpisode }>(
    `/api/v1/recovery/${episodeId}/follow-up`,
    {},
  );
}

export async function listReviews(pending = true) {
  return getJson<import("@/types").HumanReview[]>(`/api/v1/reviews?pending=${pending}`);
}

export async function resolveReview(reviewId: string, note: string) {
  return postJson<import("@/types").HumanReview>(`/api/v1/reviews/${reviewId}/resolve`, {
    note,
  });
}

export async function listAgents() {
  return getJson<import("@/types").AgentDescriptor[]>("/api/v1/agents");
}

export async function listTraces() {
  return getJson<import("@/types").WorkflowTrace[]>("/api/v1/traces");
}

export async function getRuntimeStatus() {
  return getJson<import("@/types").RuntimeStatus>("/api/v1/runtime/status");
}

export async function getRuntimeHistory(limit = 25, episodeId?: string) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (episodeId) {
    params.set("episode_id", episodeId);
  }
  return getJson<{ items: import("@/types").AdkWorkerTelemetry[] }>(
    `/api/v1/runtime/history?${params.toString()}`,
  );
}

export async function bootstrapDemo(fastForward = false) {
  return postJson<import("@/types").DemoBootstrapResponse>("/api/v1/demo/bootstrap", {
    fast_forward: fastForward,
  });
}

export async function advanceDemoFollowUp(episodeId: string) {
  return postJson<import("@/types").DemoAdvanceResponse>(
    `/api/v1/demo/advance-follow-up/${episodeId}`,
    {},
  );
}

export async function simulateConcerningSignal(episodeId: string) {
  return postJson<{
    published: string;
    episode_id: string;
    signal?: { pain_score: number; reported_issue: string };
  }>(`/api/v1/demo/concerning-signal/${episodeId}`, {});
}

export async function retryDemoVoice(episodeId: string) {
  return postJson<{ retried: boolean; episode_id: string; event: string }>(
    `/api/v1/demo/retry-voice/${episodeId}`,
    {},
  );
}

export async function simulatePromptInjection(episodeId: string) {
  return postJson<{ published: string; episode_id: string }>(
    `/api/v1/security/demo/prompt-injection/${episodeId}`,
    {},
  );
}
