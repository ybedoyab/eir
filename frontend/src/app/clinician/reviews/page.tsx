"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { listReviews, resolveReview } from "@/services/api";
import type { HumanReview } from "@/types";

export default function ClinicianReviewsPage() {
  const [reviews, setReviews] = useState<HumanReview[]>([]);

  async function refresh() {
    setReviews(await listReviews(true));
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <section className="space-y-6">
      <PageHeader eyebrow="Clinician workspace" title="Review queue" />
      <div className="grid gap-4">
        {reviews.map((review) => (
          <Card key={review.id}>
            <CardHeader title={review.reason} description={`Episode ${review.episode_id}`} />
            <p className="text-sm text-slate-600">Capability: {review.capability}</p>
            <Button
              className="mt-4"
              onClick={async () => {
                await resolveReview(review.id, "Clinician reviewed in demo workspace.");
                await refresh();
              }}
            >
              Resolve review
            </Button>
          </Card>
        ))}
      </div>
    </section>
  );
}
