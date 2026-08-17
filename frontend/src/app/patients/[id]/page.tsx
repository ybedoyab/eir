"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { episodeBadgeClass } from "@/lib/status";
import { createRecovery, getPatient } from "@/services/api";
import type { Patient, RecoveryEpisode } from "@/types";

export default function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [id, setId] = useState<string>("");
  const [patient, setPatient] = useState<Patient | null>(null);
  const [episode, setEpisode] = useState<RecoveryEpisode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    void params.then((value) => setId(value.id));
  }, [params]);

  useEffect(() => {
    if (!id) {
      return;
    }
    getPatient(id)
      .then(setPatient)
      .catch((err: Error) => setError(err.message));
  }, [id]);

  async function startRecovery() {
    if (!id) {
      return;
    }
    setCreating(true);
    setError(null);
    try {
      setEpisode(await createRecovery(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "create failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Patient profile"
        title={patient?.name ?? "Patient"}
        description="Synthetic record used for recovery workflow demos."
        actions={
          patient ? (
            <Button onClick={() => void startRecovery()} disabled={creating}>
              {creating ? "Starting…" : "Start recovery episode"}
            </Button>
          ) : null
        }
      />

      {error ? <ErrorAlert message={error} /> : null}

      {patient ? (
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <Card>
            <CardHeader title="Demographics" description="Non-clinical demo metadata." />
            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-sm text-slate-500">Patient ID</dt>
                <dd className="mt-1 font-mono text-sm text-slate-800">{patient.id}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Date of birth</dt>
                <dd className="mt-1 text-sm font-medium text-slate-800">{patient.date_of_birth}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Language</dt>
                <dd className="mt-1 text-sm font-medium text-slate-800">
                  {patient.preferred_language}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Contact channel</dt>
                <dd className="mt-1 text-sm font-medium capitalize text-slate-800">
                  {patient.preferred_contact_channel}
                </dd>
              </div>
            </dl>
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              SYNTHETIC — not real patient data.
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Recovery"
              description="Launch a new episode or open the active workflow."
            />
            {episode ? (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-slate-500">Latest episode</p>
                  <Link
                    href={`/recovery/${episode.id}`}
                    className="mt-2 block font-mono text-sm text-teal-700 hover:text-teal-800"
                  >
                    {episode.id}
                  </Link>
                </div>
                <Badge className={episodeBadgeClass(episode.status)}>{episode.status}</Badge>
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                No episode yet. Start one to trigger outreach and risk assessment.
              </p>
            )}
          </Card>
        </div>
      ) : null}
    </section>
  );
}
