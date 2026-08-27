"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
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
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Operations"
        title="Recovery"
        description="Monitor episode state, risk posture, and pending human review tasks."
        density="staff"
      />

      {error ? <ErrorAlert message={`API unavailable: ${error}`} /> : null}

      <div className="grid gap-7 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="flex flex-col">
          <SectionHeader
            level="major"
            title="Episodes"
            description="Active and historical recovery workflows."
            meta={`${episodes.length} on record`}
          />
          {loading ? (
            <CardSkeleton rows={5} />
          ) : episodes.length === 0 ? (
            <EmptyState
              title="No episodes yet"
              description="Start a recovery episode from a patient profile."
              action={
                <Link
                  href="/patients"
                  className="focus-ink -my-2 inline-flex min-h-11 items-center gap-1.5 text-sm font-medium text-accent hover:text-ink"
                >
                  Go to patients
                  <Icon name="chevronRight" size={14} />
                </Link>
              }
            />
          ) : (
            <div className="flex flex-col">
              {episodes.map((episode) => (
                <Link
                  key={episode.id}
                  href={`/recovery/${episode.id}`}
                  className="focus-ink grid min-h-[60px] grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-rule hover:bg-hover"
                >
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate font-mono text-[12.5px] text-ink">{episode.id}</span>
                    <span className="truncate font-mono text-[0.75rem] text-muted">
                      patient {episode.patient_id}
                    </span>
                  </span>
                  <span className="flex flex-wrap justify-end gap-2">
                    <Badge className={episodeBadgeClass(episode.status)}>{episode.status}</Badge>
                    <Badge className={riskBadgeClass(episode.risk_level)}>
                      {episode.risk_level}
                    </Badge>
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="flex flex-col">
          <SectionHeader
            level="major"
            title="Pending review"
            description="Human-in-the-loop checkpoints requiring approval."
            meta={reviews.length ? `${reviews.length} parked` : "nothing parked"}
          />
          {reviews.length === 0 ? (
            <EmptyState
              title="No pending reviews"
              description="Escalated episodes will appear here."
            />
          ) : (
            <div className="flex flex-col gap-5">
              {reviews.map((review) => (
                <div
                  key={review.id}
                  className="flex flex-col gap-3 border-l-[3px] border-high bg-raised px-4 py-3.5"
                >
                  <p className="text-[0.875rem] leading-[1.55] text-ink">{review.reason}</p>
                  <p className="font-mono text-[11.5px] text-muted">
                    {review.agent_name} · {review.capability}
                  </p>
                  <Button
                    className="w-fit"
                    onClick={() => {
                      void resolveReview(review.id, "resolved from UI").then(() => refresh());
                    }}
                  >
                    <Icon name="approve" size={16} />
                    Resolve and resume
                  </Button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
