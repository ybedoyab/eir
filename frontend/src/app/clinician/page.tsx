"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { listPatients, listRecovery, listReviews } from "@/services/api";
import type { HumanReview, Patient, RecoveryEpisode } from "@/types";

export default function ClinicianHomePage() {
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);

  useEffect(() => {
    void Promise.all([listReviews(true), listRecovery(), listPatients()]).then(
      ([reviewItems, episodeItems, patientItems]) => {
        setReviews(reviewItems);
        setEpisodes(episodeItems.filter((item) => item.status === "ESCALATED"));
        setPatients(patientItems);
      },
    );
  }, []);

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Clinician workspace"
        title="Needs attention"
        description="Reviews, escalated recoveries, and recent synthetic patients."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Human reviews" />
          <div className="space-y-3">
            {reviews.slice(0, 5).map((review) => (
              <div key={review.id} className="rounded-xl border border-slate-200 p-4">
                <p className="text-sm font-medium text-slate-900">{review.reason}</p>
                <p className="mt-1 text-xs text-slate-500">Episode {review.episode_id.slice(0, 8)}</p>
              </div>
            ))}
            {!reviews.length ? <p className="text-sm text-slate-500">No pending reviews.</p> : null}
          </div>
          <Link href="/clinician/reviews" className="mt-4 inline-block">
            <Button variant="secondary">Open review queue</Button>
          </Link>
        </Card>
        <Card>
          <CardHeader title="Escalated recovery episodes" />
          <div className="space-y-3">
            {episodes.slice(0, 5).map((episode) => (
              <div key={episode.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-4">
                <div>
                  <p className="font-medium text-slate-900">{episode.patient_id}</p>
                  <Badge className="mt-2 bg-amber-50 text-amber-800 ring-amber-200">{episode.risk_level}</Badge>
                </div>
                <Link href={`/recovery/${episode.id}`}>
                  <Button variant="secondary">Review</Button>
                </Link>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <Card>
        <CardHeader title="Patients" description="Synthetic demo patients." />
        <div className="grid gap-3 sm:grid-cols-2">
          {patients.map((patient) => (
            <Link
              key={patient.id}
              href={`/clinician/patients/${patient.id}`}
              className="rounded-xl border border-slate-200 p-4 transition hover:border-teal-200 hover:bg-teal-50/40"
            >
              <p className="font-medium text-slate-900">{patient.name}</p>
              <p className="text-sm text-slate-500">{patient.id}</p>
            </Link>
          ))}
        </div>
      </Card>
    </section>
  );
}
