"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { loadSession } from "@/lib/auth";
import { createRecovery, listRecovery } from "@/services/api";
import type { RecoveryEpisode } from "@/types";

export default function PatientRecoveryPage() {
  const [episodes, setEpisodes] = useState<RecoveryEpisode[]>([]);
  const session = loadSession();

  useEffect(() => {
    void listRecovery()
      .then((items) => setEpisodes(items.filter((item) => item.patient_id === session?.patient_id)))
      .catch(() => setEpisodes([]));
  }, [session?.patient_id]);

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Recovery module"
        title="Recovery follow-up"
        description="Longitudinal outreach, risk review, and clinician escalation remain available without change."
        actions={
          <Button
            onClick={async () => {
              if (!session?.patient_id) return;
              const episode = await createRecovery(session.patient_id);
              window.location.href = `/recovery/${episode.id}`;
            }}
          >
            Start recovery episode
          </Button>
        }
      />
      <div className="grid gap-4">
        {episodes.map((episode) => (
          <Card key={episode.id}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium text-slate-900">Episode {episode.id.slice(0, 8)}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge className="bg-teal-50 text-teal-800 ring-teal-200">{episode.status}</Badge>
                  <Badge className="bg-slate-50 text-slate-700 ring-slate-200">{episode.risk_level}</Badge>
                </div>
              </div>
              <Link href={`/recovery/${episode.id}`}>
                <Button variant="secondary">Open episode</Button>
              </Link>
            </div>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader
          title="Guided demo"
          description="The end-to-end recovery story demo is still available for judges and operators."
        />
        <Link href="/demo">
          <Button variant="secondary">Open recovery demo</Button>
        </Link>
      </Card>
    </section>
  );
}
