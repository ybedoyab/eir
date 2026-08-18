export type EpisodeStatus =
  | "ACTIVE"
  | "WAITING"
  | "WAITING_FOR_NEXT_FOLLOWUP"
  | "ESCALATED"
  | "COMPLETED"
  | "CANCELLED";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ContactChannel = "voice" | "sms" | "email";

export interface Patient {
  id: string;
  name: string;
  date_of_birth: string;
  preferred_language: string;
  preferred_contact_channel: ContactChannel;
}

export interface RecoveryEpisode {
  id: string;
  patient_id: string;
  status: EpisodeStatus;
  started_at: string;
  next_follow_up_at: string | null;
  risk_level: RiskLevel;
  assigned_agents: string[];
}

export interface DomainEvent {
  event_id: string;
  event_type: string;
  episode_id: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface HumanReview {
  id: string;
  episode_id: string;
  reason: string;
  capability: string;
  agent_name: string;
  status: "pending" | "resolved";
  created_at: string;
  resolved_at: string | null;
  note: string;
}

export interface AgentDescriptor {
  name: string;
  version: string;
  capabilities: string[];
  risk_level: string;
  description: string;
}

export interface WorkflowTrace {
  workflow_id: string;
  episode_id: string;
  trace_id: string;
  agent_name: string;
  event_type: string;
  timestamp: string;
  status: string;
}

export interface AdkWorkerTelemetry {
  timestamp: string;
  service: string;
  model: string;
  model_location: string;
  capability: string;
  agent_name: string;
  tools_invoked: string[];
  success: boolean;
  used_direct_fallback: boolean;
  episode_id?: string;
  trace_id?: string;
  error_type?: string | null;
  error_message?: string | null;
}

export interface RuntimeStatus {
  adk_worker: AdkWorkerTelemetry | null;
  content_guard: {
    adapter: string;
    managed_model_armor_available: boolean;
  };
  model_armor: {
    mode: string;
    location: string;
    template: string;
    available: boolean;
    last_screening_success: boolean | null;
    last_error_type?: string | null;
    last_filter_category?: string | null;
    last_blocked?: boolean | null;
  };
  fleet: {
    gemini_model: string;
    gemini_location: string;
    vertex_probe_success: boolean;
    adk_mode: string;
    adk_allow_direct_fallback: boolean;
    runtime_region: string;
    event_bus: string;
    fhir_mode: string;
    pubsub_handle: boolean;
    workflow_subscriber: string;
  };
}
