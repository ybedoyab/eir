"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatCard, StatStrip } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { displayPatientId } from "@/lib/format";
import { eventLabel, eventOutcome } from "@/lib/eventLabels";
import { episodeStatus, riskStatus, STATUS_VIEWS } from "@/lib/statusLabels";
import { getRecovery, listRecoveryEvents, listReviews, triggerFollowUp } from "@/services/api";
import type { DomainEvent, HumanReview, RecoveryEpisode } from "@/types";

function formatWhen(value: string | null | undefined): string {
  if (!value) {
    return "Not scheduled";
  }
  return new Date(value).toLocaleString();
}

function latestEventOfType(events: DomainEvent[], type: string): DomainEvent | undefined {
  return [...events].reverse().find((event) => event.event_type === type);
}

export default function RecoveryEpisodePage({
  params,
}: {
  params: Promise<{ episodeId: string }>;
}) {
  const [episodeId, setEpisodeId] = useState("");
  const [episode, setEpisode] = useState<RecoveryEpisode | null>(null);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function refresh(id: string) {
    try {
      setError(null);
      setEpisode(await getRecovery(id));
      setEvents(await listRecoveryEvents(id));
      setReviews(await listReviews(true));
    } catch (err) {
      setError(getErrorMessage(err, ERROR_MESSAGES.recovery));
    }
  }

  useEffect(() => {
    void params.then((value) => setEpisodeId(value.episodeId));
  }, [params]);

  useEffect(() => {
    if (episodeId) {
      void refresh(episodeId);
    }
  }, [episodeId]);

  const pendingReview = useMemo(
    () => reviews.find((review) => review.episode_id === episodeId && review.status === "pending"),
    [reviews, episodeId],
  );

  const latestContact = latestEventOfType(events, "PatientResponded");
  const latestAdherence = latestEventOfType(events, "AdherenceConcernDetected");
  const latestRisk = latestEventOfType(events, "RiskEscalated");
  const latestSecurity = latestEventOfType(events, "ContentSecurityBlocked");
  const voiceStarted = latestEventOfType(events, "VoiceCallStarted");
  const voiceConnected = latestEventOfType(events, "VoiceCallConnected");
  const voiceCompleted = latestEventOfType(events, "VoiceCallCompleted");
  const voiceFailedEvent = latestEventOfType(events, "VoiceCallFailed");

  const criticalMedications =
    latestRisk?.payload.reason === "critical_medication_adherence" &&
    Array.isArray(latestRisk.payload.medications)
      ? latestRisk.payload.medications
          .map((item) =>
            typeof item === "object" && item && "name" in item ? String(item.name) : "",
          )
          .filter(Boolean)
          .join(", ")
      : "";

  async function runFollowUp() {
    if (!episode) {
      return;
    }
    setRunning(true);
    try {
      await triggerFollowUp(episode.id);
      await refresh(episode.id);
    } catch (err) {
      setError(getErrorMessage(err, ERROR_MESSAGES.followUp));
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Proactive recovery episode"
        title="Recovery workflow"
        description={
          episode
            ? `Episode ${episode.id} · patient ${displayPatientId(episode.patient_id)}`
            : episodeId
              ? `Episode ${episodeId}`
              : "Loading episode…"
        }
        density="staff"
        actions={
          episode ? (
            <div className="flex flex-col items-end gap-1.5">
              <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
                Demo control
              </span>
              <Button variant="secondary" onClick={() => void runFollowUp()} disabled={running}>
                {running ? "Simulating…" : "Simulate follow-up now"}
              </Button>
            </div>
          ) : null
        }
      />

      {error ? <ErrorAlert message={error} /> : null}

      {episode ? (
        <>
          <section className="mb-7 flex flex-col">
            <SectionHeader
              level="major"
              title="Autonomous monitoring"
              description="EIR monitors this episode proactively. Cloud Scheduler and the worker fleet trigger outreach when the follow-up window is due — clinicians do not need to press a button for normal operation."
            />
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <p className="text-[1.0625rem] leading-[1.5] text-ink">
                Next autonomous follow-up{" "}
                <span className="font-mono text-[0.9375rem]">
                  {formatWhen(episode.next_follow_up_at)}
                </span>
              </p>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={episodeStatus(episode.status)} />
                <StatusBadge status={riskStatus(episode.risk_level)} />
              </div>
            </div>
          </section>

          <StatStrip className="mb-7 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Assigned agents"
              value={episode.assigned_agents.length}
              hint={episode.assigned_agents.join(", ") || "none assigned yet"}
            />
            <StatCard
              label="Latest contact"
              value={latestContact ? "yes" : "none"}
              tone={latestContact ? "ok" : "ink"}
              hint={
                latestContact
                  ? formatWhen(latestContact.occurred_at)
                  : "the patient has not responded yet"
              }
            />
            <StatCard
              label="Adherence signal"
              value={
                latestAdherence
                  ? String(latestAdherence.payload.medication_adherence ?? "flagged")
                  : String(latestContact?.payload.medication_adherence ?? "none")
              }
              tone={latestAdherence ? "warn" : "ink"}
              hint={
                latestAdherence
                  ? criticalMedications
                    ? `critical: ${criticalMedications}`
                    : "recorded; no critical medication"
                  : "no adherence concern recorded"
              }
            />
            <StatCard
              label="Risk assessment"
              value={
                latestRisk
                  ? String(latestRisk.payload.risk_level ?? episode.risk_level)
                  : episode.risk_level
              }
              tone={
                episode.risk_level === "CRITICAL"
                  ? "crit"
                  : episode.risk_level === "HIGH"
                    ? "high"
                    : episode.risk_level === "MEDIUM"
                      ? "warn"
                      : "ok"
              }
              hint={
                latestRisk
                  ? `last raised ${formatWhen(latestRisk.occurred_at)}`
                  : "no escalation on this episode"
              }
            />
          </StatStrip>

          {voiceStarted || voiceConnected || voiceCompleted || voiceFailedEvent ? (
            <section className="mb-7 flex flex-col">
              <SectionHeader
                level="major"
                title="Voice outreach"
                meta={
                  voiceCompleted
                    ? "completed"
                    : voiceFailedEvent
                      ? "failed"
                      : voiceConnected
                        ? "connected"
                        : "started"
                }
              />
              <dl className="grid grid-cols-[168px_minmax(0,1fr)] gap-x-5 gap-y-2 font-mono text-[0.8125rem]">
                <dt className="text-muted">provider</dt>
                <dd className="text-ink">
                  {String(
                    voiceStarted?.payload.provider ?? voiceCompleted?.payload.provider ?? "voximplant",
                  )}
                </dd>
                <dt className="text-muted">started</dt>
                <dd className="text-ink">
                  {voiceStarted ? formatWhen(voiceStarted.occurred_at) : "—"}
                </dd>
                <dt className="text-muted">connected</dt>
                <dd className="text-ink">
                  {voiceConnected ? formatWhen(voiceConnected.occurred_at) : "—"}
                </dd>
                <dt className="text-muted">
                  {voiceFailedEvent && !voiceCompleted ? "failed" : "completed"}
                </dt>
                <dd className={voiceFailedEvent && !voiceCompleted ? "text-high" : "text-ink"}>
                  {voiceCompleted
                    ? formatWhen(voiceCompleted.occurred_at)
                    : voiceFailedEvent
                      ? formatWhen(voiceFailedEvent.occurred_at)
                      : "—"}
                </dd>
                <dt className="text-muted">gemini_live_model</dt>
                <dd className="truncate text-ink">
                  {String(
                    voiceStarted?.payload.gemini_live_model ??
                      voiceCompleted?.payload.gemini_live_model ??
                      "gemini-live-2.5-flash-native-audio",
                  )}
                </dd>
              </dl>
              {latestContact?.payload.issue_summary || voiceCompleted?.payload.issue_summary ? (
                <div className="mt-5 flex flex-col gap-2 border-l-[3px] border-rule-strong bg-raised px-4 py-3.5">
                  <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
                    Structured summary
                  </span>
                  <p className="text-[0.875rem] leading-[1.6] text-body">
                    {String(
                      latestContact?.payload.issue_summary ??
                        voiceCompleted?.payload.issue_summary ??
                        "",
                    )}
                  </p>
                </div>
              ) : null}
            </section>
          ) : null}

          <section className="mb-7 flex flex-col">
            <SectionHeader level="major" title="Human review" />
            <div className="flex flex-wrap items-center gap-3">
              {pendingReview ? (
                <>
                  <StatusBadge status={STATUS_VIEWS.reviewNeeded} />
                  <span className="text-[0.875rem] text-secondary">{pendingReview.reason}</span>
                </>
              ) : (
                <StatusBadge status={STATUS_VIEWS.noPendingReview} />
              )}
              {latestSecurity ? (
                <StatusBadge status={STATUS_VIEWS.securityBlocked} />
              ) : null}
            </div>
          </section>
        </>
      ) : null}

      <section className="flex flex-col">
        <SectionHeader
          level="major"
          title="Episode timeline"
          description="Human-readable stages with technical event names."
          meta={events.length ? `${events.length} events` : undefined}
        />
        {events.length === 0 ? (
          <EmptyState
            title="No events yet"
            description="When the scheduler marks a follow-up due, autonomous outreach events will appear here."
          />
        ) : (
          <ol className="flex flex-col">
            {events.map((event) => {
              const label = eventLabel(event.event_type);
              return (
                <li
                  key={event.event_id}
                  className="grid gap-2 border-b border-rule py-[18px] sm:grid-cols-[168px_minmax(0,1fr)] sm:gap-5"
                >
                  <span className="flex flex-col gap-1">
                    <span className="font-mono text-[0.75rem] text-muted">{event.occurred_at}</span>
                    <span className="font-mono text-[0.75rem] text-inactive">{event.event_type}</span>
                  </span>
                  <div className="min-w-0">
                    <p className="text-[0.9375rem] leading-[1.5] text-ink">{label.title}</p>
                    <p className="mt-1 text-[13.5px] leading-[1.55] text-secondary">
                      {label.description}
                    </p>
                    <p className="mt-2 font-mono text-[11.5px] text-muted">
                      outcome · {eventOutcome(event)}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </section>
  );
}
