import { loadSession } from "@/lib/auth";
import { API_CONFIG, API_ROUTES, HTTP_STATUS } from "@/config/app";
import { ApiError, ERROR_MESSAGES } from "@/lib/errors";
import type {
  AccessMessageResponse,
  AccessSession,
  AdminSnapshot,
  Appointment,
  AuthSession,
  SlotOption,
} from "@/lib/auth";

import type {
  DomainEvent,
  HumanReview,
  InventoryItem,
  ReplenishmentCase,
  Supplier,
} from "@/types";

const AUTH_FAILURE_STATUSES: ReadonlySet<number> = new Set(Object.values(HTTP_STATUS));

function authHeaders(): Record<string, string> {
  const session = typeof window !== "undefined" ? loadSession() : null;
  const headers: Record<string, string> = {
    [API_CONFIG.headers.contentType]: API_CONFIG.headers.json,
  };
  if (session?.token) {
    headers[API_CONFIG.headers.authorization] = `${API_CONFIG.authScheme} ${session.token}`;
  }
  return headers;
}

async function getJson<T>(path: string, authenticated = false): Promise<T> {
  const response = await fetch(`${API_CONFIG.baseUrl}${path}`, {
    cache: "no-store",
    headers: authenticated ? authHeaders() : undefined,
  });
  if (!response.ok) {
    throw new ApiError(path, response.status);
  }
  return response.json();
}

async function postJson<T>(path: string, body: unknown, authenticated = false): Promise<T> {
  const response = await fetch(`${API_CONFIG.baseUrl}${path}`, {
    method: "POST",
    headers: authenticated
      ? authHeaders()
      : { [API_CONFIG.headers.contentType]: API_CONFIG.headers.json },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(path, response.status);
  }
  return response.json();
}

export async function getHealth(): Promise<{ status: string }> {
  return getJson(API_ROUTES.health);
}

export async function loginDemo(username: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_CONFIG.baseUrl}${API_ROUTES.auth.login}`, {
    method: "POST",
    headers: { [API_CONFIG.headers.contentType]: API_CONFIG.headers.json },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(ERROR_MESSAGES.login);
  }
  const body = await response.json();
  return {
    token: body.token,
    role: body.role,
    display_name: body.display_name,
    patient_id: body.patient_id,
  };
}

export interface CurrentUser {
  sub: string;
  name: string;
  role: string;
  patient_id?: string | null;
  permissions: string[];
  exp: number;
}

/**
 * Verify the stored token against the server.
 *
 * Returns null when it is absent, expired, or rejected. Demo tokens last 24h
 * and carry their own `exp`, so a stale localStorage session still looks
 * perfectly valid to the client — only the server can settle it.
 */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  if (typeof window === "undefined" || !loadSession()?.token) {
    return null;
  }
  const response = await fetch(`${API_CONFIG.baseUrl}${API_ROUTES.auth.me}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (AUTH_FAILURE_STATUSES.has(response.status)) {
    return null;
  }
  if (!response.ok) {
    throw new ApiError(API_ROUTES.auth.me, response.status);
  }
  return response.json();
}

export async function listDemoUsers() {
  return getJson<
    Array<{
      username: string;
      display_name: string;
      role: string;
      password_hint: string;
    }>
  >(API_ROUTES.auth.demoUsers);
}

export async function listPatients() {
  return getJson<import("@/types").Patient[]>(API_ROUTES.patients, true);
}

export async function getPatient(id: string) {
  return getJson<import("@/types").Patient>(`${API_ROUTES.patients}/${id}`, true);
}

export async function listPatientMedications(patientId: string) {
  return getJson<import("@/types").PatientMedication[]>(
    `${API_ROUTES.patients}/${encodeURIComponent(patientId)}/medications`,
    true,
  );
}

export async function listAppointments() {
  return getJson<Appointment[]>(API_ROUTES.appointments, true);
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
  return getJson<SlotOption[]>(`${API_ROUTES.appointmentAvailability}?${query.toString()}`, true);
}

export async function bookAppointment(slotId: string) {
  return postJson<Appointment>(API_ROUTES.appointments, { slot_id: slotId }, true);
}

export async function rescheduleAppointment(appointmentId: string, slotId: string) {
  return postJson<Appointment>(
    `${API_ROUTES.appointments}/${appointmentId}/reschedule`,
    { slot_id: slotId },
    true,
  );
}

export async function cancelAppointment(appointmentId: string, reason: string) {
  return postJson<Appointment>(
    `${API_ROUTES.appointments}/${appointmentId}/cancel`,
    { confirmed: true, reason },
    true,
  );
}

export async function createAccessSession() {
  return postJson<AccessSession>(API_ROUTES.accessSessions, { channel: "web" }, true);
}

export async function sendAccessMessage(sessionId: string, message: string) {
  return postJson<AccessMessageResponse>(
    `${API_ROUTES.accessSessions}/${sessionId}/message`,
    { message },
    true,
  );
}

export async function getAdminSnapshot() {
  return getJson<AdminSnapshot>(API_ROUTES.adminSnapshot, true);
}

export async function listRecovery() {
  return getJson<import("@/types").RecoveryEpisode[]>(API_ROUTES.recovery);
}

export async function getRecovery(id: string) {
  return getJson<import("@/types").RecoveryEpisode>(`${API_ROUTES.recovery}/${id}`);
}

export async function listRecoveryEvents(id: string) {
  return getJson<import("@/types").DomainEvent[]>(`${API_ROUTES.recovery}/${id}/events`);
}

export async function createRecovery(patientId: string) {
  return postJson<import("@/types").RecoveryEpisode>(API_ROUTES.recovery, {
    patient_id: patientId,
  });
}

export async function triggerFollowUp(episodeId: string) {
  return postJson<{ episode: import("@/types").RecoveryEpisode }>(
    `${API_ROUTES.recovery}/${episodeId}/follow-up`,
    {},
  );
}

// Reuses the generic event endpoint — RecoveryVideoRequested is a registered event type,
// so no dedicated backend route is needed for on-demand regeneration.
// `force` bypasses the backend's content-addressed cache, so an explicit "Regenerate" click
// really calls Veo instead of handing back the identical clip. First-time generation leaves it
// off so repeat episodes with the same care tasks reuse one stored video.
export async function requestRecoveryVideo(episodeId: string, force = false) {
  return postJson<import("@/types").DomainEvent>(`${API_ROUTES.recovery}/${episodeId}/events`, {
    event_type: "RecoveryVideoRequested",
    payload: force ? { force: true } : {},
  });
}

export function recoveryVideoUrl(path: string): string {
  return `${API_CONFIG.baseUrl}${path}`;
}

export async function listReviews(pending = true) {
  return getJson<import("@/types").HumanReview[]>(`${API_ROUTES.reviews}?pending=${pending}`);
}

export async function resolveReview(reviewId: string, note: string) {
  return postJson<import("@/types").HumanReview>(`${API_ROUTES.reviews}/${reviewId}/resolve`, {
    note,
  });
}

export async function listAgents() {
  return getJson<import("@/types").AgentDescriptor[]>(API_ROUTES.agents);
}

export async function listTraces() {
  return getJson<import("@/types").WorkflowTrace[]>(API_ROUTES.traces);
}

export async function getRuntimeStatus() {
  return getJson<import("@/types").RuntimeStatus>(API_ROUTES.runtimeStatus);
}

export async function getRuntimeHistory(limit = 25, episodeId?: string) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (episodeId) {
    params.set("episode_id", episodeId);
  }
  return getJson<{ items: import("@/types").AdkWorkerTelemetry[] }>(
    `${API_ROUTES.runtimeHistory}?${params.toString()}`,
  );
}

export async function bootstrapDemo(fastForward = false) {
  return postJson<import("@/types").DemoBootstrapResponse>(API_ROUTES.demoBootstrap, {
    fast_forward: fastForward,
  });
}

export async function getDemoContext(episodeId: string) {
  return getJson<{
    episode_id: string;
    patient_id: string;
    medications: import("@/types").PatientMedication[];
  }>(`${API_ROUTES.demoContext}/${encodeURIComponent(episodeId)}`);
}

export async function advanceDemoFollowUp(episodeId: string) {
  return postJson<import("@/types").DemoAdvanceResponse>(
    `${API_ROUTES.demoFollowUp}/${episodeId}`,
    {},
  );
}

export async function simulateConcerningSignal(episodeId: string) {
  return postJson<{
    published: string;
    episode_id: string;
    signal?: { pain_score: number; reported_issue: string };
  }>(`${API_ROUTES.demoSignal}/${episodeId}`, {});
}

export async function retryDemoVoice(episodeId: string) {
  return postJson<{ retried: boolean; episode_id: string; event: string }>(
    `${API_ROUTES.demoVoiceRetry}/${episodeId}`,
    {},
  );
}

export async function simulatePromptInjection(episodeId: string) {
  return postJson<{ published: string; episode_id: string }>(
    `${API_ROUTES.promptInjection}/${episodeId}`,
    {},
  );
}

export interface VoiceWebConfig {
  enabled: boolean;
  login: string;
  number: string;
  transport: string;
  gemini_live_model: string;
  gemini_live_voice: string;
}

export interface VoiceWebSession {
  login: string;
  hash: string;
  number: string;
  correlation_id: string;
  custom_data: string;
}

export async function getVoiceWebConfig() {
  return getJson<VoiceWebConfig>(API_ROUTES.voiceWebSession);
}

/**
 * Authorize a browser check-in on one episode. Pass a Voximplant one-time key to
 * also get a server-signed login hash; omit it once the client is registered.
 */
export async function startVoiceWebSession(episodeId: string, oneTimeKey = "") {
  return postJson<VoiceWebSession>(
    API_ROUTES.voiceWebSession,
    { episode_id: episodeId, one_time_key: oneTimeKey },
    true,
  );
}

export async function listInventory() {
  return getJson<InventoryItem[]>(API_ROUTES.inventory, true);
}

export async function listLowStock() {
  return getJson<InventoryItem[]>(API_ROUTES.lowStock, true);
}

export async function listSuppliers(sku?: string) {
  const query = sku ? `?sku=${encodeURIComponent(sku)}` : "";
  return getJson<Supplier[]>(`${API_ROUTES.suppliers}${query}`, true);
}

export async function adjustStock(sku: string, delta: number, reason = "") {
  return postJson<InventoryItem>(
    `${API_ROUTES.inventory}/${encodeURIComponent(sku)}/adjust`,
    { delta, reason },
    true,
  );
}

export async function listReplenishmentCases(openOnly = false) {
  return getJson<ReplenishmentCase[]>(`${API_ROUTES.supplyCases}?open_only=${openOnly}`, true);
}

export async function getReplenishmentCase(caseId: string) {
  return getJson<ReplenishmentCase>(`${API_ROUTES.supplyCases}/${caseId}`, true);
}

export async function listReplenishmentEvents(caseId: string) {
  return getJson<DomainEvent[]>(`${API_ROUTES.supplyCases}/${caseId}/events`, true);
}

export async function listPurchaseApprovals(pending = true) {
  return getJson<HumanReview[]>(`${API_ROUTES.supplyApprovals}?pending=${pending}`, true);
}

export async function approvePurchaseOrder(caseId: string, note = "") {
  return postJson<ReplenishmentCase>(`${API_ROUTES.supplyCases}/${caseId}/approve`, { note }, true);
}

export async function receiveDelivery(caseId: string) {
  return postJson<ReplenishmentCase>(`${API_ROUTES.supplyCases}/${caseId}/receive`, {}, true);
}

export async function cancelReplenishmentCase(caseId: string, reason = "") {
  return postJson<ReplenishmentCase>(`${API_ROUTES.supplyCases}/${caseId}/cancel`, { reason }, true);
}
