"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { displayPatientId } from "@/lib/format";
import { episodeStatus } from "@/lib/statusLabels";
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
      setError(getErrorMessage(err, ERROR_MESSAGES.recoveryCreate));
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Patient profile"
        title={patient?.name ?? "Patient"}
        description="Demo record used for recovery workflow walkthroughs."
        density="staff"
        actions={
          patient ? (
            <Button onClick={() => void startRecovery()} disabled={creating}>
              {creating ? "Starting…" : "Start recovery episode"}
              <Icon name="arrowRight" size={16} />
            </Button>
          ) : null
        }
      />

      {error ? <ErrorAlert message={error} /> : null}

      {patient ? (
        <div className="grid gap-7 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="flex flex-col">
            <SectionHeader level="major" title="Demographics" meta="non-clinical demo metadata" />
            <dl className="grid grid-cols-[152px_minmax(0,1fr)] gap-x-5 gap-y-2.5 font-mono text-[0.8125rem]">
              <dt className="text-muted">patient_id</dt>
              <dd className="truncate text-ink">{displayPatientId(patient.id)}</dd>
              <dt className="text-muted">date_of_birth</dt>
              <dd className="text-ink">{patient.date_of_birth}</dd>
              <dt className="text-muted">preferred_language</dt>
              <dd className="text-ink">{patient.preferred_language}</dd>
              <dt className="text-muted">contact_channel</dt>
              <dd className="text-ink">{patient.preferred_contact_channel}</dd>
            </dl>
            <p className="mt-5 inline-flex w-fit items-center bg-ink px-2.5 py-1.5 font-mono text-[0.75rem] uppercase tracking-[0.06em] text-paper">
              Demo record — not real patient data
            </p>
          </section>

          <section className="flex flex-col">
            <SectionHeader
              level="major"
              title="Recovery"
              description="Launch a new episode or open the active workflow."
            />
            {episode ? (
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
                    Latest episode
                  </span>
                  <Link
                    href={`/recovery/${episode.id}`}
                    className="focus-ink -my-2 inline-flex min-h-11 w-fit items-center gap-2 font-mono text-[0.8125rem] text-accent hover:text-ink"
                  >
                    {episode.id}
                    <Icon name="open" size={14} />
                  </Link>
                </div>
                <StatusBadge status={episodeStatus(episode.status)} />
              </div>
            ) : (
              <p className="text-[0.875rem] leading-[1.6] text-secondary">
                No episode yet. Start one to trigger outreach and risk assessment.
              </p>
            )}
          </section>
        </div>
      ) : null}
    </section>
  );
}
