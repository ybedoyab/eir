"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { episodeBadgeClass, riskBadgeClass } from "@/lib/status";
import { getRecovery, listRecoveryEvents, triggerFollowUp } from "@/services/api";
import type { DomainEvent, RecoveryEpisode } from "@/types";

export default function RecoveryEpisodePage({
  params,
}: {
  params: Promise<{ episodeId: string }>;
}) {
  const [episodeId, setEpisodeId] = useState("");
  const [episode, setEpisode] = useState<RecoveryEpisode | null>(null);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function refresh(id: string) {
    try {
      setError(null);
      setEpisode(await getRecovery(id));
      setEvents(await listRecoveryEvents(id));
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
        eyebrow="Episode detail"
        title="Recovery workflow"
        description={episodeId ? `Episode ${episodeId}` : "Loading episode…"}
        actions={
          episode ? (
            <Button onClick={() => void runFollowUp()} disabled={running}>
              {running ? "Running follow-up…" : "Run follow-up"}
            </Button>
          ) : null
        }
      />

      {error ? <ErrorAlert message={error} /> : null}

      {episode ? (
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Status</p>
            <div className="mt-2">
              <Badge className={episodeBadgeClass(episode.status)}>{episode.status}</Badge>
            </div>
          </Card>
          <Card className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Risk</p>
            <div className="mt-2">
              <Badge className={riskBadgeClass(episode.risk_level)}>{episode.risk_level}</Badge>
            </div>
          </Card>
          <Card className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Patient</p>
            <p className="mt-2 font-mono text-sm text-slate-800">{episode.patient_id}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Assigned agents</p>
            <p className="mt-2 text-sm text-slate-800">
              {episode.assigned_agents.join(", ") || "None yet"}
            </p>
          </Card>
        </div>
      ) : null}

      <Card>
        <CardHeader title="Event timeline" description="Domain events emitted by the recovery fleet." />
        {events.length === 0 ? (
          <EmptyState
            title="No events yet"
            description="Run a follow-up to populate outreach and risk events."
          />
        ) : (
          <ol className="relative space-y-4 border-l border-slate-200 pl-5">
            {events.map((event) => (
              <li key={event.event_id} className="relative">
                <span className="absolute -left-[1.37rem] top-1.5 h-2.5 w-2.5 rounded-full bg-teal-600 ring-4 ring-white" />
                <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-900">{event.event_type}</p>
                    <p className="font-mono text-xs text-slate-400">{event.occurred_at}</p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </section>
  );
}
