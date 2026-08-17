"use client";

import { useEffect, useState } from "react";

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

  async function refresh(id: string) {
    try {
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

  return (
    <section>
      <h1>Recovery episode</h1>
      {error ? <p>API unavailable: {error}</p> : null}
      {episode ? (
        <>
          <p>ID: {episode.id}</p>
          <p>Patient: {episode.patient_id}</p>
          <p>
            Status: {episode.status} / risk {episode.risk_level}
          </p>
          <p>Agents: {episode.assigned_agents.join(", ") || "none yet"}</p>
          <button
            type="button"
            onClick={() => {
              void triggerFollowUp(episode.id).then(() => refresh(episode.id));
            }}
          >
            Run follow-up
          </button>
        </>
      ) : null}
      <h2>Events</h2>
      <ol>
        {events.map((event) => (
          <li key={event.event_id}>
            {event.event_type} — {event.occurred_at}
          </li>
        ))}
      </ol>
    </section>
  );
}
