"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { eventLabel, eventOutcome } from "@/lib/eventLabels";
import { episodeBadgeClass, riskBadgeClass } from "@/lib/status";
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
      setError(err instanceof Error ? err.message : "load failed");
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

  async function runFollowUp() {
    if (!episode) {
      return;
    }
    setRunning(true);
    try {
      await triggerFollowUp(episode.id);
      await refresh(episode.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "follow-up failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Proactive recovery episode"
        title="Recovery workflow"
        description={
          episode
            ? `Episode ${episode.id} · patient ${episode.patient_id}`
            : episodeId
              ? `Episode ${episodeId}`
              : "Loading episode…"
        }
        actions={
          episode ? (
            <div className="flex flex-col items-end gap-1">
              <span className="text-[11px] uppercase tracking-wide text-slate-400">Demo control</span>
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
          <Card className="mb-6 border-teal-200 bg-gradient-to-br from-teal-50/80 to-white p-5">
            <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
              <div>
                <p className="text-xs uppercase tracking-wide text-teal-700">Autonomous monitoring</p>
                <h2 className="mt-2 text-xl font-semibold text-slate-900">
                  Next autonomous follow-up: {formatWhen(episode.next_follow_up_at)}
                </h2>
                <p className="mt-2 max-w-2xl text-sm text-slate-600">
                  EIR monitors this episode proactively. Cloud Scheduler and the worker fleet
                  trigger outreach when the follow-up window is due — clinicians do not need to
                  press a button for normal operation.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-white/80 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Current state</p>
                  <div className="mt-2">
                    <Badge className={episodeBadgeClass(episode.status)}>{episode.status}</Badge>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white/80 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Risk level</p>
                  <div className="mt-2">
                    <Badge className={riskBadgeClass(episode.risk_level)}>{episode.risk_level}</Badge>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Assigned agents</p>
              <p className="mt-2 text-sm text-slate-800">
                {episode.assigned_agents.join(", ") || "None yet"}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Latest patient contact</p>
              <p className="mt-2 text-sm text-slate-800">
                {latestContact ? formatWhen(latestContact.occurred_at) : "No response yet"}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Latest adherence signal</p>
              <p className="mt-2 text-sm text-slate-800">
                {latestAdherence ? formatWhen(latestAdherence.occurred_at) : "No concern recorded"}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Latest risk assessment</p>
              <p className="mt-2 text-sm text-slate-800">
                {latestRisk
                  ? String(latestRisk.payload.risk_level ?? episode.risk_level)
                  : episode.risk_level}
              </p>
            </Card>
          </div>

          {voiceStarted || voiceConnected || voiceCompleted || voiceFailedEvent ? (
            <Card className="mb-6 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Voice outreach</p>
              <dl className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
                <div>Provider: {String(voiceStarted?.payload.provider ?? voiceCompleted?.payload.provider ?? "voximplant")}</div>
                <div>
                  Status:{" "}
                  {voiceCompleted
                    ? "completed"
                    : voiceFailedEvent
                      ? "failed"
                      : voiceConnected
                        ? "connected"
                        : "started"}
                </div>
                <div>Started: {voiceStarted ? formatWhen(voiceStarted.occurred_at) : "—"}</div>
                <div>Connected: {voiceConnected ? formatWhen(voiceConnected.occurred_at) : "—"}</div>
                <div>
                  {voiceCompleted
                    ? `Completed: ${formatWhen(voiceCompleted.occurred_at)}`
                    : voiceFailedEvent
                      ? `Failed: ${formatWhen(voiceFailedEvent.occurred_at)}`
                      : "Completed: —"}
                </div>
                <div>
                  Gemini Live model:{" "}
                  {String(
                    voiceStarted?.payload.gemini_live_model ??
                      voiceCompleted?.payload.gemini_live_model ??
                      "gemini-live-2.5-flash-native-audio",
                  )}
                </div>
              </dl>
              {latestContact?.payload.issue_summary || voiceCompleted?.payload.issue_summary ? (
                <div className="mt-4 rounded-xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Structured summary</p>
                  <p className="mt-2 text-sm leading-6 text-slate-800">
                    {String(latestContact?.payload.issue_summary ?? voiceCompleted?.payload.issue_summary ?? "")}
                  </p>
                </div>
              ) : null}
            </Card>
          ) : null}

          <Card className="mb-6 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Human review</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {pendingReview ? (
                <>
                  <Badge className="bg-amber-50 text-amber-800 ring-amber-200">Review needed</Badge>
                  <span className="text-sm text-slate-700">{pendingReview.reason}</span>
                </>
              ) : (
                <Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">No pending review</Badge>
              )}
              {latestSecurity ? (
                <Badge className="bg-rose-50 text-rose-700 ring-rose-200">
                  Security block recorded
                </Badge>
              ) : null}
            </div>
          </Card>
        </>
      ) : null}

      <Card>
        <CardHeader title="Episode timeline" description="Human-readable stages with technical event names." />
        {events.length === 0 ? (
          <EmptyState
            title="No events yet"
            description="When the scheduler marks a follow-up due, autonomous outreach events will appear here."
          />
        ) : (
          <ol className="relative space-y-4 border-l border-slate-200 pl-5">
            {events.map((event) => {
              const label = eventLabel(event.event_type);
              return (
                <li key={event.event_id} className="relative">
                  <span className="absolute -left-[1.37rem] top-1.5 h-2.5 w-2.5 rounded-full bg-teal-600 ring-4 ring-white" />
                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-slate-900">{label.title}</p>
                        <p className="mt-1 text-sm text-slate-600">{label.description}</p>
                        <p className="mt-2 font-mono text-[11px] uppercase tracking-wide text-slate-400">
                          {event.event_type}
                        </p>
                      </div>
                      <p className="font-mono text-xs text-slate-400">{event.occurred_at}</p>
                    </div>
                    <p className="mt-3 text-xs text-slate-500">Outcome: {eventOutcome(event)}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </Card>
    </section>
  );
}
