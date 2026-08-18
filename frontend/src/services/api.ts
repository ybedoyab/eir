const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

export async function listPatients() {
  return getJson<import("@/types").Patient[]>("/api/v1/patients");
}

export async function getPatient(id: string) {
  return getJson<import("@/types").Patient>(`/api/v1/patients/${id}`);
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

export async function simulatePromptInjection(episodeId: string) {
  return postJson<{ published: string; episode_id: string }>(
    `/api/v1/security/demo/prompt-injection/${episodeId}`,
    {},
  );
}
