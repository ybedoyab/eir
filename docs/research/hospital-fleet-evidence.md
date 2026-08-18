# Hospital fleet design evidence

This document summarizes research relevant to EIR's hospital access product direction. Each item is labeled as **evidence**, **product inference**, or **EIR design decision**.

## Appointment access and no-shows

**Evidence [R1]:** Dantas et al. (2018, *Health Policy*, PMID 29482948) reviewed no-show literature and found missed appointments remain a persistent scheduling problem with multifactorial causes.

**Product inference:** Reducing friction for reschedule/cancel and reminder confirmation can address a portion of missed visits without replacing clinical judgment.

**EIR design decision:** Provide appointment read, reschedule, cancel, and reminder workflows in one patient access surface across web and future voice.

## Reminders

**Evidence [R2]:** McLean et al. (2016, *Patient Preference and Adherence*, PMID 27110102) found reminder systems improve attendance but are not uniformly optimized across channels and timing.

**EIR design decision:** Reuse existing scheduler/event patterns for synthetic in-app reminders rather than building a separate notification platform this sprint.

## Web self-scheduling

**Evidence [R3]:** Zhao et al. (2017, *JMIR*, PMID 28446422) reviewed web-based appointment systems and reported usability and adoption vary by system design and patient population.

**Evidence:** Digital self-scheduling adoption can differ across demographic and socioeconomic groups.

**Product inference:** A single channel does not guarantee equitable access.

**EIR design decision:** Offer web portal plus future voice channel; do not claim voice alone resolves digital-health inequity.

## Patient portals

**Evidence [R4]:** Carini et al. (2020, *JMIR*, PMID 33174851) umbrella review found patient portals can improve engagement but evidence quality and outcomes vary.

**Evidence [R7]:** Milicia et al. (2026, *Applied Clinical Informatics*, PMID 41999669) reported usability gaps in major EHR patient portal experiences.

**EIR design decision:** Patient UI uses plain language, shallow navigation, visible confirmation states, and no infrastructure jargon.

## Conversational agents in care

**Evidence [R5]:** Li et al. (2023, *International Journal of Nursing Studies*, PMID 37146391) reviewed AI conversational agents and found feasibility with safety and evaluation gaps.

**Evidence [R6]:** Wang et al. (2024, *JMIR*, PMID 39509695) highlighted healthcare opportunities and concerns for LLM conversational systems, including safety and overreach.

**EIR design decision:** Administrative actions run through deterministic services with backend authorization. Clinical symptom severity does not autonomously create urgent bookings.

## FHIR scheduling semantics

**Evidence [R8]:** HL7 FHIR R4 defines `Schedule`, `Slot`, and `Appointment` as the standard booking model.

**EIR design decision:** Synthetic hospital fixtures and adapters use FHIR R4 semantics rather than a parallel proprietary schema.

## Accessibility

**Evidence [R9]:** W3C WCAG 2.2 provides accessibility requirements for web content.

**EIR design decision:** Target WCAG 2.2 AA patterns: semantic HTML, visible focus, keyboard-usable controls, confirmation for destructive actions, and no icon-only critical controls.

## Architecture separation

**EIR design decision:** `RecoveryEpisode` remains the longitudinal recovery workflow. `PatientAccessSession` handles routine hospital access without forcing administrative requests into recovery episodes.

## Security posture

**EIR design decision:** Demo RBAC is enforced server-side with signed sessions. Model Armor is defense-in-depth and does not replace authorization. Full voice transcripts are not persisted.

## References

- [R1] Dantas et al., 2018, PMID 29482948
- [R2] McLean et al., 2016, PMID 27110102
- [R3] Zhao et al., 2017, PMID 28446422
- [R4] Carini et al., 2020, PMID 33174851
- [R5] Li et al., 2023, PMID 37146391
- [R6] Wang et al., 2024, PMID 39509695
- [R7] Milicia et al., 2026, PMID 41999669
- [R8] HL7 FHIR R4 Appointment / Schedule / Slot
- [R9] W3C WCAG 2.2
