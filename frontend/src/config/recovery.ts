import type { EpisodeStatus } from "@/types";

export const RECOVERY_EVENTS = {
  appointmentRequested: "AppointmentRequested",
  completed: "RecoveryEpisodeCompleted",
  episodeStarted: "RecoveryEpisodeStarted",
  followUpDue: "FollowUpDue",
  patientResponded: "PatientResponded",
  videoFailed: "RecoveryVideoFailed",
  videoReady: "RecoveryVideoReady",
  videoRequested: "RecoveryVideoRequested",
} as const;

export const TERMINAL_RECOVERY_STATUSES = new Set<EpisodeStatus>(["COMPLETED", "CANCELLED"]);

export const PATIENT_SAFE_RECOVERY_EVENTS = new Set<string>([
  RECOVERY_EVENTS.episodeStarted,
  RECOVERY_EVENTS.patientResponded,
  RECOVERY_EVENTS.followUpDue,
  RECOVERY_EVENTS.appointmentRequested,
  RECOVERY_EVENTS.completed,
  RECOVERY_EVENTS.videoReady,
  RECOVERY_EVENTS.videoFailed,
]);

export const RECOVERY_VIDEO_EVENTS = new Set<string>([
  RECOVERY_EVENTS.videoReady,
  RECOVERY_EVENTS.videoRequested,
  RECOVERY_EVENTS.videoFailed,
]);

export const RECOVERY_VIDEO_TIMING = {
  pollIntervalMs: 4_000,
  pollTimeoutMs: 180_000,
} as const;
