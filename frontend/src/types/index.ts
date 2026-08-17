export type EpisodeStatus =
  | "ACTIVE"
  | "WAITING"
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
