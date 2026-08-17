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
