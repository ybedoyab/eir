const EVENT_LABELS: Record<string, { title: string; description: string }> = {
  InventoryLevelLow: {
    title: "Stock crossed the reorder point",
    description: "Stock monitor opened a replenishment case for this medication.",
  },
  ReplenishmentRequested: {
    title: "Replenishment sized",
    description: "Inventory agent sized the order against usage and supplier lead time.",
  },
  SupplierContacted: {
    title: "Supplier called",
    description: "Procurement agent placed an outbound call to a vendor.",
  },
  SupplierQuoteReceived: {
    title: "Quotes recorded",
    description: "Prices and availability captured from the supplier calls.",
  },
  SupplierUnavailable: {
    title: "No supplier could fulfil",
    description: "Sourcing failed; a human buyer has to take the case.",
  },
  PurchaseOrderDrafted: {
    title: "Purchase order drafted",
    description: "Procurement agent selected a supplier and prepared the order.",
  },
  SupplyApprovalGranted: {
    title: "Purchase authorized",
    description: "Operations approved the drafted order before it was placed.",
  },
  PurchaseOrderApproved: {
    title: "Purchase order placed",
    description: "The authorized order was sent to the supplier.",
  },
  RestockScheduled: {
    title: "Restock scheduled",
    description: "Delivery window confirmed for the placed order.",
  },
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
    title: "Voice outreach started",
    description: "The recovery fleet requested an outbound voice check-in.",
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
  if (event.event_type === "InventoryLevelLow") {
    return `${String(event.payload.on_hand ?? "?")} on hand · reorder point ${String(
      event.payload.reorder_point ?? "?",
    )}`;
  }
  if (event.event_type === "ReplenishmentRequested") {
    return `Requested ${String(event.payload.quantity ?? "?")} ${String(
      event.payload.unit ?? "units",
    )}`;
  }
  if (event.event_type === "SupplierContacted") {
    return `Called ${String(event.payload.supplier_name ?? "supplier")}`;
  }
  if (event.event_type === "SupplierQuoteReceived") {
    return `${String(event.payload.quote_count ?? 0)} quote(s) recorded`;
  }
  if (event.event_type === "SupplierUnavailable") {
    return String(event.payload.reason ?? "No supplier could fulfil");
  }
  if (event.event_type === "PurchaseOrderDrafted") {
    return String(event.payload.selection_reason ?? "Draft prepared");
  }
  if (event.event_type === "SupplyApprovalGranted") {
    return `Authorized by ${String(event.payload.approved_by ?? "operations")}`;
  }
  if (event.event_type === "PurchaseOrderApproved") {
    return `${String(event.payload.purchase_order_id ?? "Order")} placed · ${String(
      event.payload.total_cost ?? "",
    )} ${String(event.payload.currency ?? "")}`.trim();
  }
  if (event.event_type === "RestockScheduled") {
    return `Expected in ${String(event.payload.lead_time_days ?? "?")} day(s)`;
  }
  if (event.event_type === "ContentSecurityBlocked") {
    const category = String(event.payload.filter_category ?? event.payload.reason ?? "blocked");
    return `Blocked by ${String(event.payload.adapter ?? "content guard")} (${category})`;
  }
  if (event.event_type === "PatientResponded") {
    const pain = event.payload.pain_score;
    const adherence = String(event.payload.medication_adherence ?? "").trim();
    const issue = String(event.payload.issue_summary ?? "").trim();
    const bits = [`Channel: ${String(event.payload.channel ?? "unknown")}`];
    if (pain !== undefined && pain !== null) {
      bits.push(`pain ${String(pain)}/10`);
    }
    if (adherence) {
      bits.push(`medications ${adherence}`);
    } else if (issue) {
      bits.push(issue);
    }
    return bits.join(" · ");
  }
  if (event.event_type === "AdherenceConcernDetected") {
    const meds = event.payload.medications;
    if (Array.isArray(meds) && meds.length) {
      const names = meds
        .map((item) =>
          typeof item === "object" && item && "name" in item
            ? String((item as { name?: string }).name)
            : "",
        )
        .filter(Boolean);
      if (names.length) {
        return `Missed: ${names.join(", ")}`;
      }
    }
    return `Adherence: ${String(event.payload.medication_adherence ?? "no")}`;
  }
  if (event.event_type === "RiskEscalated") {
    return `Risk level: ${String(event.payload.risk_level ?? "HIGH")}`;
  }
  if (event.event_type === "FollowUpDue") {
    return "Autonomous outreach scheduled";
  }
  if (event.event_type === "VoiceCallStarted") {
    const provider = String(event.payload.provider ?? "unknown");
    const transport = String(event.payload.transport ?? "").trim();
    return transport ? `Provider: ${provider} · ${transport}` : `Provider: ${provider}`;
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
