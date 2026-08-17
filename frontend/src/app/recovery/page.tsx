"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { episodeBadgeClass, riskBadgeClass } from "@/lib/status";
import { listRecovery, listReviews, resolveReview } from "@/services/api";
import type { HumanReview, RecoveryEpisode } from "@/types";

export default function RecoveryPage() {
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      setError(null);
      setEpisodes(await listRecovery());
      setReviews(await listReviews(true));
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <section>
      <PageHeader
        eyebrow="Operations"
        title="Recovery"
        description="Monitor episode state, risk posture, and pending human review tasks."
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader
            title="Episodes"
            description="Active and historical recovery workflows."
          />
          {loading ? (
            <p className="text-sm text-slate-500">Loading episodes…</p>
          ) : episodes.length === 0 ? (
            <EmptyState
              title="No episodes yet"
              description="Start a recovery episode from a patient profile."
              action={
                <Link
                  href="/patients"
                  className="text-sm font-medium text-teal-700 hover:text-teal-800"
                >
                  Go to patients
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {episodes.map((episode) => (
                <Link
                  key={episode.id}
                  href={`/recovery/${episode.id}`}
                  className="block rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 transition hover:border-teal-200 hover:bg-white"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-mono text-xs text-slate-400">{episode.id}</p>
                      <p className="mt-1 text-sm text-slate-600">Patient {episode.patient_id}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge className={episodeBadgeClass(episode.status)}>{episode.status}</Badge>
                      <Badge className={riskBadgeClass(episode.risk_level)}>
                        {episode.risk_level}
                      </Badge>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <CardHeader
            title="Pending review"
            description="Human-in-the-loop checkpoints requiring approval."
          />
          {reviews.length === 0 ? (
            <EmptyState title="No pending reviews" description="Escalated episodes will appear here." />
          ) : (
            <div className="space-y-3">
              {reviews.map((review) => (
                <div
                  key={review.id}
                  className="rounded-xl border border-rose-100 bg-rose-50/60 px-4 py-3"
                >
                  <p className="text-sm font-medium text-slate-900">{review.reason}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {review.agent_name} · {review.capability}
                  </p>
                  <Button
                    variant="danger"
                    className="mt-3"
                    onClick={() => {
                      void resolveReview(review.id, "resolved from UI").then(() => refresh());
                    }}
                  >
                    Resolve review
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </section>
  );
}
