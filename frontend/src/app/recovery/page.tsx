"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listRecovery, listReviews, resolveReview } from "@/services/api";
import type { HumanReview, RecoveryEpisode } from "@/types";

export default function RecoveryPage() {
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setEpisodes(await listRecovery());
      setReviews(await listReviews(true));
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <section>
      <h1>Recovery episodes</h1>
      {error ? <p>API unavailable: {error}</p> : null}
      <h2>Episodes</h2>
      <ul>
        {episodes.map((episode) => (
          <li key={episode.id}>
            <Link href={`/recovery/${episode.id}`}>
              {episode.id} — {episode.status} / {episode.risk_level}
            </Link>
          </li>
        ))}
      </ul>
      <h2>Pending human review</h2>
      {reviews.length === 0 ? <p>None.</p> : null}
      <ul>
        {reviews.map((review) => (
          <li key={review.id}>
            {review.reason} ({review.agent_name})
            <button
              type="button"
              onClick={() => {
                void resolveReview(review.id, "resolved from UI").then(() => refresh());
              }}
            >
              Resolve
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
