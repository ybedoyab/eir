const EVENT_LABELS: Record<string, { title: string; description: string }> = {
  RecoveryEpisodeStarted: {
    title: "Recovery monitoring started",
    description: "EIR opened a longitudinal recovery episode.",
  },
  FollowUpDue: {
    title: "Autonomous follow-up due",
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
    title: "Risk escalation",
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
    title: "Security block",
    description: "Model Armor blocked unsafe ingress before any tool execution.",
  },
  RecoveryEpisodeCompleted: {
    title: "Recovery episode completed",
    description: "The recovery workflow reached a terminal state.",
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
    return `Channel: ${String(event.payload.channel ?? "unknown")}`;
  }
  if (event.event_type === "RiskEscalated") {
    return `Risk level: ${String(event.payload.risk_level ?? "HIGH")}`;
  }
  if (event.event_type === "FollowUpDue") {
    return "Autonomous outreach scheduled";
  }
  return "Recorded";
}
