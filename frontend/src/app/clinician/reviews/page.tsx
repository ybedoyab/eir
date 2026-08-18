"use client";

import { CheckCircle2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { formatWait } from "@/lib/format";
import { episodeStatus, riskStatus } from "@/lib/statusLabels";
import { listPatients, listRecovery, listReviews, resolveReview } from "@/services/api";
import type { HumanReview, Patient, RecoveryEpisode } from "@/types";

export default function ClinicianReviewsPage() {
  const { toast } = useToast();
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [reviewItems, episodeItems, patientItems] = await Promise.all([
        listReviews(true),
        listRecovery(),
        listPatients(),
      ]);
      setReviews(reviewItems);
      setEpisodes(episodeItems);
      setPatients(patientItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load reviews");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const names = useMemo(
    () => Object.fromEntries(patients.map((item) => [item.id, item.name])),
    [patients],
  );

  async function resolve(id: string) {
    if (busyId) return;
    setBusyId(id);
    try {
      await resolveReview(id, "Clinician reviewed in demo workspace.");
      toast("Review resolved");
      await refresh();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not resolve review", "error");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Clinician workspace"
        title="Review queue"
        description="Human review requests from recovery and risk signals."
      />
      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}
      {loading ? (
        <CardSkeleton rows={4} />
      ) : reviews.length ? (
        <div className="grid gap-4">
          {reviews.map((review) => {
            const episode = episodes.find((item) => item.id === review.episode_id);
            const patientName = episode ? names[episode.patient_id] ?? "Patient" : "Patient";
            return (
              <Card key={review.id}>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex gap-3">
                    <Avatar name={patientName} />
                    <div>
                      <p className="font-semibold text-slate-900">{patientName}</p>
                      <p className="mt-1 text-sm text-slate-700">{review.reason}</p>
                      <p className="mt-2 text-xs text-slate-500">{formatWait(review.created_at)}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {episode ? <StatusBadge status={episodeStatus(episode.status)} /> : null}
                        {episode ? <StatusBadge status={riskStatus(episode.risk_level)} /> : null}
                        <StatusBadge status={{ label: "Waiting review", tone: "warning" }} />
                      </div>
                    </div>
                  </div>
                  <Button disabled={busyId === review.id} onClick={() => void resolve(review.id)}>
                    {busyId === review.id ? "Resolving…" : "Resolve"}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="You're all caught up"
          description="No pending clinician reviews."
          icon={CheckCircle2}
        />
      )}
    </section>
  );
}
