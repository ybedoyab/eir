const EVENT_LABELS: Record<string, { title: string; description: string }> = {
  RecoveryEpisodeStarted: {
    title: "Recovery monitoring started",
    description: "EIR opened a longitudinal recovery episode.",
  },
  FollowUpDue: {
    title: "Autonomous follow-up became due",
    description: "Scheduler or workflow marked the next proactive outreach window.",
  },
  PatientResponded: {
    title: "Patient response received",
    description: "Structured response captured from the outreach channel.",
  },
  AdherenceConcernDetected: {
    title: "Adherence concern",
    description: "Medication or recovery-task adherence needs attention.",
  },
  RiskEscalated: {
    title: "Recovery risk escalated",
    description: "Risk agent elevated the episode for closer monitoring.",
  },
  HumanReviewRequested: {
    title: "Clinician review requested",
    description: "Safety policy requires human review before proceeding.",
  },
  ClinicianResolved: {
    title: "Clinician review completed",
    description: "A clinician cleared or adjusted the pending action.",
  },
  AppointmentRequested: {
    title: "Follow-up appointment",
    description: "Scheduling agent requested a follow-up visit.",
  },
  ContentSecurityBlocked: {
    title: "Security threat blocked",
    description: "Model Armor blocked unsafe ingress before any tool execution.",
  },
  RecoveryEpisodeCompleted: {
    title: "Recovery episode completed",
    description: "The recovery workflow reached a terminal state.",
  },
  VoiceCallStarted: {
    title: "Phone outreach started",
    description: "The recovery fleet requested a real outbound PSTN call.",
  },
  VoiceCallConnected: {
    title: "Call connected",
    description: "The patient answered. Gemini Live is on the call.",
  },
  VoiceCallCompleted: {
    title: "Voice check-in completed",
    description: "Structured recovery signals were submitted from the live call.",
  },
  VoiceCallFailed: {
    title: "Voice outreach failed",
    description: "The outbound call did not complete. No recovery data was invented.",
  },
};

export function eventLabel(eventType: string): { title: string; description: string } {
  return (
    EVENT_LABELS[eventType] ?? {
      title: eventType.replace(/([A-Z])/g, " $1").trim(),
      description: "Workflow event recorded by the recovery fleet.",
    }
  );
}

export function eventOutcome(event: { event_type: string; payload: Record<string, unknown> }): string {
  if (event.event_type === "ContentSecurityBlocked") {
    const category = String(event.payload.filter_category ?? event.payload.reason ?? "blocked");
    return `Blocked by ${String(event.payload.adapter ?? "content guard")} (${category})`;
  }
  if (event.event_type === "PatientResponded") {
    const pain = event.payload.pain_score;
    const issue = String(event.payload.issue_summary ?? "").trim();
    if (pain !== undefined && pain !== null) {
      return `Channel: ${String(event.payload.channel ?? "unknown")} · pain ${String(pain)}/10`;
    }
    return issue
      ? `Channel: ${String(event.payload.channel ?? "unknown")} · ${issue}`
      : `Channel: ${String(event.payload.channel ?? "unknown")}`;
  }
  if (event.event_type === "RiskEscalated") {
    return `Risk level: ${String(event.payload.risk_level ?? "HIGH")}`;
  }
  if (event.event_type === "FollowUpDue") {
    return "Autonomous outreach scheduled";
  }
  if (event.event_type === "VoiceCallStarted") {
    return `Provider: ${String(event.payload.provider ?? "unknown")}`;
  }
  if (event.event_type === "VoiceCallCompleted") {
    const pain = event.payload.pain_score;
    if (pain !== undefined && pain !== null) {
      return `Structured check-in received · pain ${String(pain)}/10`;
    }
    return "Structured check-in received";
  }
  if (event.event_type === "VoiceCallFailed") {
    return `Outcome: ${String(event.payload.failure_reason ?? event.payload.state ?? "failed")}`;
  }
  return "Recorded";
}
