import type { IconName } from "@/components/ui/Icon";
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

export interface RecoveryRecommendationCategory {
  id: string;
  label: string;
  icon: IconName;
  /** First category whose pattern matches a care-plan item wins, so order is precedence. */
  match: RegExp;
}

/**
 * Themes the patient-facing "Recommendations" section groups care-plan items under.
 *
 * Precedence matters. `rest` sits above `activity` so "Ice after activity" reads as rest
 * rather than exercise, and `appointment` uses `\bclinic\b` so "Await clinician review"
 * falls to `monitoring` instead of being filed as a visit.
 */
export const RECOVERY_RECOMMENDATION_CATEGORIES: RecoveryRecommendationCategory[] = [
  {
    id: "medication",
    label: "Medication",
    icon: "pill",
    match: /medicat|medicine|prescri|dose|dosage|pill|tablet|inhaler/i,
  },
  {
    id: "monitoring",
    label: "Watch for",
    icon: "alertCircle",
    match: /report|symptom|worsening|monitor|watch|temperature|fever|bleed|swelling|pain score|review|await/i,
  },
  {
    id: "appointment",
    label: "Appointments",
    icon: "schedule",
    match: /appointment|follow-up visit|follow up visit|\bvisit\b|\bclinic\b|reschedul/i,
  },
  {
    id: "rest",
    label: "Rest and recovery",
    icon: "clock",
    match: /\brest\b|\bice\b|hydrat|fluid|sleep|elevate/i,
  },
  {
    id: "activity",
    label: "Activity",
    icon: "activity",
    match: /walk|exercise|activity|movement|stretch|physio|steps|mobil/i,
  },
];

export const RECOVERY_RECOMMENDATION_FALLBACK: RecoveryRecommendationCategory = {
  id: "general",
  label: "Care plan",
  icon: "checkCircle",
  match: /.^/,
};

/**
 * Baseline guidance shown when the episode's own care plan does not cover a theme.
 *
 * Kept identical to `_GENERIC_TASKS` in `agents/eir_agents/recovery_video/handler.py` so the
 * page and the Veo narration never tell the patient two different things. This is generic
 * post-procedure guidance, never generated advice — agents do not diagnose, and neither
 * does this page.
 */
export const BASELINE_RECOVERY_GUIDANCE: string[] = [
  "Rest and stay hydrated",
  "Take medications as prescribed",
  "Contact your care team about any new or worsening symptoms",
];
