"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import {
  agentChain,
  armorLabel,
  chainToolLabel,
  currentStepIndex,
  DEMO_ATTACK_PROMPT,
  DEMO_POLL_MS,
  DEMO_STALL_MS,
  DEMO_STEPS,
  DEMO_STORAGE_KEY,
  demoActivity,
  deriveDemoSteps,
  formatWhen,
  latestEvent,
  outreachProof,
  runtimeProof,
  shortEpisodeId,
} from "@/lib/demoStory";
import { eventLabel } from "@/lib/eventLabels";
import { cn } from "@/lib/cn";
import { episodeBadgeClass, riskBadgeClass } from "@/lib/status";
import {
  advanceDemoFollowUp,
  bootstrapDemo,
  getPatient,
  getRecovery,
  getRuntimeHistory,
  getRuntimeStatus,
  listRecoveryEvents,
  listReviews,
  resolveReview,
  simulateConcerningSignal,
  simulatePromptInjection,
} from "@/services/api";
import type {
  AdkWorkerTelemetry,
  DomainEvent,
  HumanReview,
  Patient,
  RecoveryEpisode,
  RuntimeStatus,
} from "@/types";

type AwaitKind = "follow-up" | "attack" | "concerning" | "review" | null;
type BusyKind = "start" | "advance" | "attack" | "concerning" | "review" | null;

function isConflict(error: unknown): boolean {
  return error instanceof Error && error.message.includes("(409)");
}

export default function DemoPage() {
  const [episodeId, setEpisodeId] = useState<string | null>(null);
  const [episode, setEpisode] = useState<RecoveryEpisode | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [history, setHistory] = useState<AdkWorkerTelemetry[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<BusyKind>(null);
  const [awaiting, setAwaiting] = useState<AwaitKind>(null);
  const [stalled, setStalled] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const awaitingSince = useRef<number | null>(null);

  const completed = useMemo(
    () => deriveDemoSteps({ episode, events, history, reviews }),
    [episode, events, history, reviews],
  );
  const stepIndex = currentStepIndex(completed);
  const activity = demoActivity({ completed, events, history, awaiting });
  const pendingReview = reviews.find(
    (review) => review.episode_id === episodeId && review.status === "pending",
  );
  const securityEvent = latestEvent(events, "ContentSecurityBlocked");
  const outreach = outreachProof(history);
  const chain = agentChain(history);
  const proof = runtime ? runtimeProof(runtime) : [];
  const armor = armorLabel(
    String(securityEvent?.payload.adapter ?? history.find((item) => item.security_adapter)?.security_adapter ?? ""),
  );

  const refresh = useCallback(async (id: string) => {
    const [nextEpisode, nextEvents, nextHistory, nextReviews, nextRuntime] = await Promise.all([
      getRecovery(id),
      listRecoveryEvents(id),
      getRuntimeHistory(25, id),
      listReviews(true),
      getRuntimeStatus(),
    ]);
    setEpisode(nextEpisode);
    setEvents(nextEvents);
    setHistory(nextHistory.items);
    setReviews(nextReviews.filter((review) => review.episode_id === id));
    setRuntime(nextRuntime);
    try {
      setPatient(await getPatient(nextEpisode.patient_id));
    } catch {
      setPatient(null);
    }
  }, []);

  useEffect(() => {
    const stored = sessionStorage.getItem(DEMO_STORAGE_KEY);
    setHydrated(true);
    if (!stored) {
      void getRuntimeStatus()
        .then(setRuntime)
        .catch(() => undefined);
      return;
    }
    setEpisodeId(stored);
    void refresh(stored).catch(() => {
      sessionStorage.removeItem(DEMO_STORAGE_KEY);
      setEpisodeId(null);
    });
  }, [refresh]);

  useEffect(() => {
    if (!episodeId) {
      return;
    }
    const waiting = awaiting !== null;
    const intervalMs = waiting ? DEMO_POLL_MS : 4000;
    const timer = window.setInterval(() => {
      void refresh(episodeId).catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "refresh failed");
      });
      if (waiting && awaitingSince.current && Date.now() - awaitingSince.current > DEMO_STALL_MS) {
        setStalled(true);
      }
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [episodeId, awaiting, refresh]);

  useEffect(() => {
    if (awaiting === "follow-up" && completed[3]) {
      setAwaiting(null);
      setStalled(false);
    }
    if (awaiting === "attack" && completed[4]) {
      setAwaiting(null);
      setStalled(false);
    }
    if (awaiting === "concerning" && (completed[5] || completed[6])) {
      setAwaiting(null);
      setStalled(false);
    }
    if (awaiting === "review" && events.some((event) => event.event_type === "ClinicianResolved")) {
      setAwaiting(null);
      setStalled(false);
    }
  }, [awaiting, completed, events]);

  function beginAwait(kind: AwaitKind) {
    awaitingSince.current = Date.now();
    setAwaiting(kind);
    setStalled(false);
  }

  async function startDemo() {
    setBusy("start");
    setError(null);
    try {
      const boot = await bootstrapDemo(false);
      sessionStorage.setItem(DEMO_STORAGE_KEY, boot.episode_id);
      setEpisodeId(boot.episode_id);
      await refresh(boot.episode_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start demo");
    } finally {
      setBusy(null);
    }
  }

  async function fastForward() {
    if (!episodeId) {
      return;
    }
    setBusy("advance");
    setError(null);
    try {
      await advanceDemoFollowUp(episodeId);
      beginAwait("follow-up");
      await refresh(episodeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fast-forward failed");
    } finally {
      setBusy(null);
    }
  }

  async function runAttack() {
    if (!episodeId) {
      return;
    }
    setBusy("attack");
    setError(null);
    try {
      await simulatePromptInjection(episodeId);
      beginAwait("attack");
      await refresh(episodeId);
    } catch (err) {
      if (isConflict(err)) {
        beginAwait("attack");
        await refresh(episodeId);
      } else {
        setError(err instanceof Error ? err.message : "Attack simulation failed");
      }
    } finally {
      setBusy(null);
    }
  }

  async function runConcerning() {
    if (!episodeId) {
      return;
    }
    setBusy("concerning");
    setError(null);
    try {
      await simulateConcerningSignal(episodeId);
      beginAwait("concerning");
      await refresh(episodeId);
    } catch (err) {
      if (isConflict(err)) {
        beginAwait("concerning");
        await refresh(episodeId);
      } else {
        setError(err instanceof Error ? err.message : "Concerning signal failed");
      }
    } finally {
      setBusy(null);
    }
  }

  async function approveReview() {
    if (!pendingReview || !episodeId) {
      return;
    }
    setBusy("review");
    setError(null);
    try {
      await resolveReview(pendingReview.id, "Clinician reviewed synthetic demo episode.");
      beginAwait("review");
      await refresh(episodeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review resolve failed");
    } finally {
      setBusy(null);
    }
  }

  const disabled = busy !== null;
  const showFastForward = Boolean(episodeId) && !completed[2];
  const showAttack = completed[3] && !completed[4];
  const showConcerning = completed[4] && !completed[5];
  const clinicianResolved = events.some((event) => event.event_type === "ClinicianResolved");

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700">
          Hackathon showcase
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          EIR — Autonomous Recovery Demo
        </h1>
        <p className="text-sm text-slate-500">
          Gemini 3.5 Flash · Google ADK · Model Armor · FHIR · Pub/Sub
        </p>
      </header>

      {error ? <ErrorAlert message={error} /> : null}

      {runtime ? (
        <Card className="p-4">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {proof.map((row) => (
              <div key={row.label} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2">
                <span className="text-sm text-slate-700">{row.label}</span>
                <span
                  className={cn(
                    "font-mono text-[11px] font-semibold tracking-wide",
                    row.live ? "text-emerald-700" : "text-slate-500",
                  )}
                >
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {!hydrated ? null : !episodeId ? (
        <Card className="border-teal-200 bg-gradient-to-br from-teal-50/80 to-white p-8">
          <p className="text-sm font-medium text-teal-800">Consultation just ended</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">Start a synthetic recovery episode</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            EIR will open a Recovery Episode, schedule proactive follow-up, and wait for the
            autonomous fleet. No real patient data.
          </p>
          <div className="mt-6">
            <Button onClick={() => void startDemo()} disabled={disabled}>
              {busy === "start" ? "Starting…" : "Start demo"}
            </Button>
          </div>
        </Card>
      ) : (
        <>
          <Card className="border-teal-200 bg-gradient-to-br from-teal-50/70 to-white">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-teal-700">
                  Monitoring started
                </p>
                <h2 className="mt-1 text-2xl font-semibold text-slate-900">
                  {patient?.name ?? "Synthetic patient"}
                </h2>
                <p className="mt-1 font-mono text-xs text-slate-500">
                  {shortEpisodeId(episodeId)} · {episode?.patient_id}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {episode ? <Badge className={episodeBadgeClass(episode.status)}>{episode.status}</Badge> : null}
                {episode ? <Badge className={riskBadgeClass(episode.risk_level)}>{episode.risk_level}</Badge> : null}
              </div>
            </div>
            <p className="mt-4 text-sm text-slate-600">
              Next autonomous follow-up: {formatWhen(episode?.next_follow_up_at)}
            </p>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <Link href={`/recovery/${episodeId}`} className="font-medium text-teal-800 hover:underline">
                Open full episode
              </Link>
              <Link href="/observability" className="font-medium text-teal-800 hover:underline">
                Open observability
              </Link>
            </div>
          </Card>

          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {DEMO_STEPS.map((step, index) => {
              const done = completed[index];
              const current = index === stepIndex && !completed.every(Boolean);
              return (
                <li
                  key={step.id}
                  className={cn(
                    "rounded-2xl border px-4 py-3",
                    done
                      ? "border-emerald-200 bg-emerald-50/80"
                      : current
                        ? "border-teal-300 bg-white shadow-sm"
                        : "border-slate-200 bg-white",
                  )}
                >
                  <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                    Step {index + 1}
                  </p>
                  <p className={cn("mt-1 text-sm font-medium", done ? "text-emerald-800" : "text-slate-800")}>
                    {step.title}
                  </p>
                </li>
              );
            })}
          </ol>

          {activity ? (
            <p className="text-sm font-medium text-teal-800">{activity}</p>
          ) : null}
          {stalled ? (
            <p className="text-sm font-medium text-amber-800">
              Still processing — check Observability
            </p>
          ) : null}

          {showFastForward ? (
            <Card>
              <h2 className="text-xl font-semibold text-slate-900">Fast-forward to follow-up</h2>
              <p className="mt-1 text-sm text-slate-500">
                Demo time control — production uses Cloud Scheduler.
              </p>
              <div className="mt-4">
                <Button onClick={() => void fastForward()} disabled={disabled}>
                  {busy === "advance" ? "Advancing…" : "Fast-forward to follow-up"}
                </Button>
              </div>
            </Card>
          ) : null}

          {completed[2] && outreach ? (
            <Card className="border-emerald-200 bg-emerald-50/50">
              <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">
                Synthetic voice simulation
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-emerald-950">
                Autonomous follow-up completed
              </h2>
              <dl className="mt-4 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
                <div>Agent: {outreach.agent_name}</div>
                <div>Model: {outreach.model}</div>
                <div>Tool: {(outreach.tools_invoked ?? []).join(", ") || "conduct_outreach"}</div>
                <div>Direct fallback: {outreach.used_direct_fallback ? "enabled" : "disabled"}</div>
                <div>Worker: {outreach.service}</div>
              </dl>
            </Card>
          ) : null}

          {showAttack ? (
            <Card>
              <h2 className="text-xl font-semibold text-slate-900">Simulate prompt-injection attack</h2>
              <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 font-mono text-sm text-slate-700">
                {DEMO_ATTACK_PROMPT}
              </p>
              <div className="mt-4">
                <Button variant="danger" onClick={() => void runAttack()} disabled={disabled}>
                  {busy === "attack" ? "Sending…" : "Simulate prompt-injection attack"}
                </Button>
              </div>
            </Card>
          ) : null}

          {securityEvent ? (
            <Card className="border-rose-200 bg-rose-50/70">
              <h2 className="text-2xl font-semibold tracking-tight text-rose-900">
                BLOCKED BY MODEL ARMOR
              </h2>
              <p className="mt-2 text-sm font-medium text-rose-800">{armor.title}</p>
              <ul className="mt-3 space-y-1 text-sm text-rose-900">
                <li>prompt injection / jailbreak</li>
                <li>no tool executed</li>
                <li>no records returned</li>
              </ul>
              <p className="mt-3 font-mono text-[11px] text-rose-700">
                adapter: {String(securityEvent.payload.adapter ?? armor.title)} ·{" "}
                {String(securityEvent.payload.filter_category ?? "prompt_injection")}
              </p>
            </Card>
          ) : null}

          {showConcerning ? (
            <Card>
              <h2 className="text-xl font-semibold text-slate-900">Simulate concerning patient response</h2>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm">Pain score: 8/10</div>
                <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm">Reported issue: swelling</div>
              </div>
              <div className="mt-4">
                <Button onClick={() => void runConcerning()} disabled={disabled}>
                  {busy === "concerning" ? "Sending…" : "Simulate concerning patient response"}
                </Button>
              </div>
            </Card>
          ) : null}

          {completed[5] ? (
            <Card className="border-amber-200 bg-amber-50/70">
              <h2 className="text-2xl font-semibold text-amber-950">EIR escalated instead of guessing</h2>
              <p className="mt-2 text-sm leading-6 text-amber-900">
                The agent detected a concerning recovery signal and routed the case to a clinician.
              </p>
            </Card>
          ) : null}

          {pendingReview ? (
            <Card className="border-amber-300 bg-white">
              <h2 className="text-xl font-semibold text-slate-900">Human review required</h2>
              <dl className="mt-3 space-y-1 text-sm text-slate-700">
                <div>Reason: {pendingReview.reason}</div>
                <div>
                  Requesting agent: {pendingReview.agent_name}
                  {pendingReview.capability ? ` · ${pendingReview.capability}` : ""}
                </div>
                <div>Current episode risk: {episode?.risk_level}</div>
                <div>Timestamp: {formatWhen(pendingReview.created_at)}</div>
              </dl>
              <div className="mt-4">
                <Button onClick={() => void approveReview()} disabled={disabled}>
                  {busy === "review" ? "Saving…" : "Approve / Mark reviewed"}
                </Button>
              </div>
            </Card>
          ) : null}

          {clinicianResolved ? (
            <Card className="border-emerald-200 bg-emerald-50/60">
              <h2 className="text-xl font-semibold text-emerald-950">Clinician review completed</h2>
              <p className="mt-2 text-sm text-emerald-800">
                Workflow resumed from the governed human-review checkpoint.
              </p>
            </Card>
          ) : null}

          {chain.length > 0 ? (
            <Card>
              <h2 className="text-base font-semibold text-slate-900">Agent chain</h2>
              <ol className="mt-4 space-y-0">
                {chain.map((item, index) => (
                  <li key={`${item.timestamp}-${item.agent_name}-${index}`}>
                    <p className="font-mono text-sm font-medium text-slate-900">{item.agent_name}</p>
                    <p className="ml-4 text-sm text-slate-600">↓ {chainToolLabel(item)}</p>
                    {index < chain.length - 1 ? <div className="ml-1 h-3 w-px bg-slate-200" /> : null}
                  </li>
                ))}
              </ol>
            </Card>
          ) : null}

          {events.length > 0 ? (
            <Card>
              <h2 className="text-base font-semibold text-slate-900">Audit timeline</h2>
              <ol className="mt-4 space-y-3">
                {events.map((event) => {
                  const label = eventLabel(event.event_type);
                  return (
                    <li key={event.event_id} className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-slate-900">{label.title}</p>
                        <p className="font-mono text-[11px] text-slate-400">{event.event_type}</p>
                      </div>
                      <p className="font-mono text-[11px] text-slate-400">{formatWhen(event.occurred_at)}</p>
                    </li>
                  );
                })}
              </ol>
            </Card>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => void startDemo()} disabled={disabled}>
              {busy === "start" ? "Starting…" : "Start new demo"}
            </Button>
          </div>
        </>
      )}

      <section className="grid gap-4 sm:grid-cols-2">
        {[
          {
            title: "Proactive",
            body: "EIR follows the patient after the visit instead of waiting for another call.",
          },
          {
            title: "Agentic",
            body: "Gemini + ADK agents inspect context and execute tools through a governed fleet.",
          },
          {
            title: "Safe",
            body: "Model Armor and deterministic policy gates block unsafe actions and escalate uncertainty.",
          },
          {
            title: "Longitudinal",
            body: "Recovery state persists across follow-ups rather than ending with one chat session.",
          },
        ].map((item) => (
          <Card key={item.title} className="p-4">
            <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{item.body}</p>
          </Card>
        ))}
      </section>
    </div>
  );
}
