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
