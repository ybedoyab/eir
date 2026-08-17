"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
    try {
      setEpisode(await createRecovery(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "create failed");
    }
  }

  return (
    <section>
      <h1>Patient</h1>
      {error ? <p>API unavailable: {error}</p> : null}
      {patient ? (
        <>
          <p>
            <strong>{patient.name}</strong> — {patient.id}
          </p>
          <p>DOB: {patient.date_of_birth}</p>
          <p>Language: {patient.preferred_language}</p>
          <p>Channel: {patient.preferred_contact_channel}</p>
          <p>SYNTHETIC — not real patient data.</p>
          <button type="button" onClick={() => void startRecovery()}>
            Start recovery episode
          </button>
        </>
      ) : null}
      {episode ? (
        <p>
          Episode created:{" "}
          <Link href={`/recovery/${episode.id}`}>{episode.id}</Link> ({episode.status})
        </p>
      ) : null}
    </section>
  );
}
