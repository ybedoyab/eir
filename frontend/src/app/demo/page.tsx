"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { loadSession, saveSession } from "@/lib/auth";
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
  demoNeedsFastPoll,
  deriveDemoSteps,
  formatWhen,
  hasEvent,
  latestEvent,
  runtimeProof,
  shortEpisodeId,
  voiceCheckin,
  voiceFailed,
  isConcerningResponse,
  isScriptedVoice,
  isVoximplantEvent,
  isWebVoiceEvent,
} from "@/lib/demoStory";
import { eventLabel } from "@/lib/eventLabels";
import { cn } from "@/lib/cn";
import { episodeBadgeClass, riskBadgeClass } from "@/lib/status";
import {
  advanceDemoFollowUp,
  bootstrapDemo,
  getDemoContext,
  getRecovery,
  getRuntimeHistory,
  getRuntimeStatus,
  listRecoveryEvents,
  listReviews,
  loginDemo,
  resolveReview,
  simulateConcerningSignal,
  simulatePromptInjection,
  retryDemoVoice,
} from "@/services/api";
import type {
  AdkWorkerTelemetry,
  DomainEvent,
  HumanReview,
  PatientMedication,
  RecoveryEpisode,
  RuntimeStatus,
} from "@/types";

const VoicePreviewClient = dynamic(() => import("../voice-preview/VoicePreviewClient"), {
  ssr: false,
  loading: () => <p className="text-sm text-slate-600">Loading live check-in…</p>,
});

type AwaitKind = "follow-up" | "attack" | "concerning" | "review" | null;
type BusyKind = "start" | "advance" | "attack" | "concerning" | "review" | "retry" | null;

function isConflict(error: unknown): boolean {
  return error instanceof Error && error.message.includes("(409)");
}

function readDemoPointer(): { episodeId: string; patientName?: string } | null {
  const raw = sessionStorage.getItem(DEMO_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as { episodeId?: string; patientName?: string };
    if (typeof parsed.episodeId === "string" && parsed.episodeId) {
      return { episodeId: parsed.episodeId, patientName: parsed.patientName };
    }
  } catch {
    // Legacy demos stored a bare episode id.
  }
  return { episodeId: raw };
}

function ActivityBanner({ title, detail }: { title: string; detail?: string }) {
  return (
    <Card className="border-teal-300 bg-teal-50 p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="mt-1.5 h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-teal-600" />
        <div>
          <p className="text-lg font-semibold text-teal-950">{title}</p>
          {detail ? <p className="mt-1 text-sm leading-6 text-teal-800">{detail}</p> : null}
        </div>
      </div>
    </Card>
  );
}

export default function DemoPage() {
  const [episodeId, setEpisodeId] = useState<string | null>(null);
  const [episode, setEpisode] = useState<RecoveryEpisode | null>(null);
  const [patientName, setPatientName] = useState<string | null>(null);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [history, setHistory] = useState<AdkWorkerTelemetry[]>([]);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<BusyKind>(null);
  const [awaiting, setAwaiting] = useState<AwaitKind>(null);
  const [stalled, setStalled] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [medications, setMedications] = useState<PatientMedication[]>([]);
  const [alexReady, setAlexReady] = useState(false);
  const awaitingSince = useRef<number | null>(null);

  const completed = useMemo(
    () => deriveDemoSteps({ episode, events, history, reviews }),
    [episode, events, history, reviews],
  );
  const stepIndex = currentStepIndex(completed);
  const pendingReview = reviews.find(
    (review) => review.episode_id === episodeId && review.status === "pending",
  );
  const clinicianResolved = hasEvent(events, "ClinicianResolved");
  const activity = demoActivity({
    completed,
    events,
    history,
    awaiting,
    pendingReview: Boolean(pendingReview),
  });
  const securityEvent = latestEvent(events, "ContentSecurityBlocked");
  const chain = agentChain(history);
  const proof = runtime ? runtimeProof(runtime) : [];
  const armor = armorLabel(
    String(securityEvent?.payload.adapter ?? history.find((item) => item.security_adapter)?.security_adapter ?? ""),
  );
  const loopComplete = completed.every(Boolean) && clinicianResolved;
  const reviewLocked = busy === "review" || awaiting === "review";
  const preparingReview = completed[4] && !pendingReview && !clinicianResolved && awaiting !== "review";
  const checkin = voiceCheckin(events);
  const callFailed = voiceFailed(events);
  const concerningFromVoice = events.some(isConcerningResponse);

  const refresh = useCallback(async (id: string) => {
    const [nextEpisode, nextEvents, nextHistory, nextReviews, nextRuntime, nextContext] = await Promise.all([
      getRecovery(id),
      listRecoveryEvents(id),
      getRuntimeHistory(25, id),
      listReviews(true),
      getRuntimeStatus(),
      getDemoContext(id).catch(() => null),
    ]);
    setEpisode(nextEpisode);
    setEvents(nextEvents);
    setHistory(nextHistory.items);
    setReviews(nextReviews.filter((review) => review.episode_id === id));
    setRuntime(nextRuntime);
    if (nextContext?.medications) {
      setMedications(nextContext.medications);
    }
  }, []);

  useEffect(() => {
    const stored = readDemoPointer();
    setHydrated(true);
    if (!stored) {
      void getRuntimeStatus()
        .then(setRuntime)
        .catch(() => undefined);
      return;
    }
    setEpisodeId(stored.episodeId);
    if (stored.patientName) {
      setPatientName(stored.patientName);
    }
    void refresh(stored.episodeId).catch(() => {
      sessionStorage.removeItem(DEMO_STORAGE_KEY);
      setEpisodeId(null);
      setPatientName(null);
    });
  }, [refresh]);

  const waiting = demoNeedsFastPoll({ awaiting, activity });

  useEffect(() => {
    if ((waiting || preparingReview) && awaitingSince.current === null) {
      awaitingSince.current = Date.now();
    }
    if (!waiting) {
      awaitingSince.current = null;
    }
  }, [waiting, preparingReview]);

  useEffect(() => {
    if (!episodeId) {
      return;
    }
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
  }, [episodeId, waiting, refresh]);

  useEffect(() => {
    if (awaiting === "follow-up" && (completed[3] || callFailed)) {
      setAwaiting(null);
      setStalled(false);
    }
    if (awaiting === "attack" && completed[6]) {
      setAwaiting(null);
      setStalled(false);
    }
    if (awaiting === "concerning" && (Boolean(pendingReview) || clinicianResolved)) {
      setAwaiting(null);
      setStalled(false);
    }
    if (awaiting === "review" && clinicianResolved) {
      setAwaiting(null);
      setBusy(null);
      setStalled(false);
    }
  }, [awaiting, completed, pendingReview, clinicianResolved, callFailed]);

  function beginAwait(kind: AwaitKind) {
    awaitingSince.current = Date.now();
    setAwaiting(kind);
    setStalled(false);
  }

  function resetLocalDemo() {
    setAwaiting(null);
    setStalled(false);
    setError(null);
    setEvents([]);
    setHistory([]);
    setReviews([]);
    setEpisode(null);
    setPatientName(null);
    setMedications([]);
    setAlexReady(false);
  }

  async function startDemo() {
    setBusy("start");
    resetLocalDemo();
    try {
      const boot = await bootstrapDemo(false);
      sessionStorage.setItem(
        DEMO_STORAGE_KEY,
        JSON.stringify({ episodeId: boot.episode_id, patientName: boot.patient_name ?? "" }),
      );
      setEpisodeId(boot.episode_id);
      setPatientName(boot.patient_name ?? null);
      setMedications(boot.medications ?? []);
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
    if (!pendingReview || !episodeId || reviewLocked) {
      return;
    }
    setBusy("review");
    setError(null);
    try {
      await resolveReview(pendingReview.id, "Clinician reviewed synthetic demo episode.");
      beginAwait("review");
      await refresh(episodeId);
    } catch (err) {
      setBusy(null);
      setError(err instanceof Error ? err.message : "Review resolve failed");
    }
  }

  async function retryVoice() {
    if (!episodeId) {
      return;
    }
    setBusy("retry");
    setError(null);
    try {
      await retryDemoVoice(episodeId);
      beginAwait("follow-up");
      await refresh(episodeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice retry failed");
    } finally {
      setBusy(null);
    }
  }

  const actionLocked = busy !== null || reviewLocked;
  const showFastForward = Boolean(episodeId) && !completed[2] && awaiting !== "follow-up";
  const voiceStarted = latestEvent(events, "VoiceCallStarted");
  const inPstnCall =
    isVoximplantEvent(voiceStarted) &&
    !hasEvent(events, "VoiceCallCompleted") &&
    !callFailed &&
    !completed[3];
  const webWaiting =
    Boolean(episodeId) &&
    !completed[3] &&
    !callFailed &&
    (isWebVoiceEvent(voiceStarted) ||
      (awaiting === "follow-up" &&
        Boolean(runtime?.fleet.voice?.browser_voice_enabled) &&
        !isVoximplantEvent(voiceStarted) &&
        !isScriptedVoice(voiceStarted)));
  const pstnCheckin = Boolean(checkin) && isVoximplantEvent(checkin) && !isScriptedVoice(checkin);
  const webCheckin = Boolean(checkin) && isWebVoiceEvent(checkin) && !isScriptedVoice(checkin);
  const showAttack = completed[3] && !completed[6] && awaiting !== "attack";
  const showConcerning =
    (callFailed || stalled || (completed[3] && !concerningFromVoice && !webWaiting)) &&
    !completed[4] &&
    awaiting !== "concerning";
  const adherenceEvent = latestEvent(events, "AdherenceConcernDetected");

  useEffect(() => {
    if (!webWaiting) {
      return;
    }
    let cancelled = false;
    async function prepareAlex() {
      try {
        const existing = loadSession();
        if (existing?.role === "PATIENT" && existing.patient_id === "patient-synthetic-001") {
          if (!cancelled) {
            setAlexReady(true);
          }
          return;
        }
        const session = await loginDemo("alex", "demo-alex");
        saveSession(session);
        if (!cancelled) {
          setAlexReady(true);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not open the in-page voice check-in");
        }
      }
    }
    void prepareAlex();
    return () => {
      cancelled = true;
    };
  }, [webWaiting]);

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-8 sm:px-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700">
            Guided Recovery Demo
          </p>
          <a href="/login" className="text-sm font-medium text-teal-700 hover:text-teal-800">
            Back to role portal
          </a>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          EIR — Autonomous Recovery Demo
        </h1>
        <p className="text-sm text-slate-500">~4 minute judge flow · synthetic identities only</p>
      </header>

      {error ? <ErrorAlert message={error} /> : null}

      {runtime ? (
        <Card className="p-3">
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {proof.map((row) => (
              <div key={row.label} className="flex items-center gap-2">
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
        <Card className="border-teal-200 bg-gradient-to-br from-teal-50/80 to-white p-6">
          <p className="text-sm font-medium text-teal-800">Consultation just ended</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">Start a synthetic recovery episode</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            EIR will open a Recovery Episode, schedule proactive follow-up, and wait for the
            autonomous fleet. No real patient data.
          </p>
          <div className="mt-5">
            <Button onClick={() => void startDemo()} disabled={actionLocked}>
              {busy === "start" ? "Starting…" : "Start demo"}
            </Button>
          </div>
        </Card>
      ) : (
        <>
          <Card className="border-teal-200 bg-gradient-to-br from-teal-50/70 to-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-teal-700">
                  Monitoring started
                </p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900">
                  {patientName || "Synthetic patient"}
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
            <p className="mt-3 text-sm text-slate-600">
              Next autonomous follow-up: {formatWhen(episode?.next_follow_up_at)}
            </p>
          </Card>

          {medications.length ? (
            <Card className="p-4">
              <h2 className="text-xl font-semibold text-slate-900">Prescribed medications</h2>
              <p className="mt-1 text-sm text-slate-500">
                The same catalog the replenishment fleet uses. Gemini asks whether medications
                were taken; names are matched after the check-in.
              </p>
              <ul className="mt-4 space-y-2">
                {medications.map((medication) => (
                  <li
                    key={`${medication.sku || medication.rxnorm_code || medication.name}`}
                    className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div>
                      <p className="font-medium text-slate-900">{medication.name}</p>
                      {medication.dose ? (
                        <p className="mt-1 text-sm text-slate-600">{medication.dose}</p>
                      ) : null}
                      {medication.sku ? (
                        <p className="mt-1 font-mono text-[11px] text-slate-400">{medication.sku}</p>
                      ) : null}
                    </div>
                    {medication.critical ? (
                      <Badge className="bg-rose-100 text-rose-800">Critical</Badge>
                    ) : null}
                  </li>
                ))}
              </ul>
              {checkin ? (
                <p className="mt-3 text-sm text-slate-700">
                  Latest adherence:{" "}
                  <span className="font-medium">
                    {String(checkin.payload.medication_adherence ?? "unknown")}
                  </span>
                  {adherenceEvent ? " · adherence agent flagged this episode" : ""}
                </p>
              ) : null}
            </Card>
          ) : null}

          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {DEMO_STEPS.map((step, index) => {
              const done = completed[index];
              const current = index === stepIndex && !completed.every(Boolean);
              return (
                <li
                  key={step.id}
                  className={cn(
                    "rounded-2xl border px-3 py-2.5",
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

          {activity ? <ActivityBanner title={activity.title} detail={activity.detail} /> : null}
          {stalled ? (
            <p className="text-sm font-medium text-amber-800">
              Still processing — check Observability
            </p>
          ) : null}

          {showFastForward ? (
            <Card className="p-4">
              <h2 className="text-xl font-semibold text-slate-900">Fast-forward to follow-up</h2>
              <p className="mt-1 text-sm text-slate-500">
                Demo time control — production uses Cloud Scheduler.
              </p>
              <div className="mt-4">
                <Button onClick={() => void fastForward()} disabled={actionLocked}>
                  {busy === "advance" ? "Advancing…" : "Fast-forward to follow-up"}
                </Button>
              </div>
            </Card>
          ) : null}

          {inPstnCall ? (
            <Card className="border-teal-300 bg-teal-50/80 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-teal-800">
                REAL VOICE OUTREACH
              </p>
              <h2 className="mt-1 text-xl font-semibold text-teal-950">
                {hasEvent(events, "VoiceCallConnected")
                  ? "Gemini Live conversation active"
                  : "Calling patient…"}
              </h2>
              <ul className="mt-3 space-y-1 text-sm text-teal-900">
                <li>Voximplant PSTN</li>
                <li>Gemini Live</li>
                <li>{runtime?.fleet.voice?.gemini_live_model || "gemini-live-2.5-flash-native-audio"}</li>
                <li>Synthetic patient · real phone call</li>
              </ul>
            </Card>
          ) : null}

          {webWaiting ? (
            <Card className="border-teal-300 bg-teal-50/40 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-teal-800">
                LIVE GEMINI CHECK-IN
              </p>
              <h2 className="mt-1 text-xl font-semibold text-teal-950">
                Answer as Alex in this tab
              </h2>
              <p className="mt-1 text-sm text-teal-900">
                WebRTC to Gemini Live — close any other Voximplant softphone first. Say pain,
                symptoms, and whether you took enoxaparin.
              </p>
              <div className="mt-4">
                {alexReady && episodeId ? (
                  <VoicePreviewClient episodeId={episodeId} compact />
                ) : (
                  <p className="text-sm text-teal-800">Preparing the in-page check-in…</p>
                )}
              </div>
            </Card>
          ) : null}

          {checkin ? (
            <Card className="border-emerald-200 bg-emerald-50/50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">
                {pstnCheckin
                  ? "REAL PHONE FOLLOW-UP COMPLETED"
                  : webCheckin
                    ? "LIVE GEMINI CHECK-IN COMPLETED"
                    : "SYNTHETIC CHECK-IN COMPLETED"}
              </p>
              <h2 className="mt-1 text-xl font-semibold text-emerald-950">
                Recovery check-in received
              </h2>
              <dl className="mt-3 grid gap-1 text-sm text-slate-700 sm:grid-cols-2">
                <div>Pain: {String(checkin.payload.pain_score ?? "—")}/10</div>
                <div>
                  Reported issue: {checkin.payload.reported_issue ? String(checkin.payload.issue_summary || "yes") : "none"}
                </div>
                <div>Medication adherence: {String(checkin.payload.medication_adherence ?? "unknown")}</div>
                <div>Provider: {String(checkin.payload.provider ?? "voice")}</div>
              </dl>
            </Card>
          ) : null}

          {callFailed ? (
            <Card className="border-amber-200 bg-amber-50/70 p-4">
              <h2 className="text-xl font-semibold text-amber-950">Voice outreach did not complete</h2>
              <p className="mt-1 text-sm text-amber-900">
                No recovery data was invented. One manual retry is available.
              </p>
              <div className="mt-4">
                <Button onClick={() => void retryVoice()} disabled={actionLocked}>
                  {busy === "retry" ? "Retrying…" : "Retry voice outreach once"}
                </Button>
              </div>
            </Card>
          ) : null}

          {showAttack ? (
            <Card className="p-4">
              <h2 className="text-xl font-semibold text-slate-900">Simulate prompt-injection attack</h2>
              <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 font-mono text-sm text-slate-700">
                {DEMO_ATTACK_PROMPT}
              </p>
              <div className="mt-4">
                <Button variant="danger" onClick={() => void runAttack()} disabled={actionLocked}>
                  {busy === "attack" ? "Sending…" : "Simulate prompt-injection attack"}
                </Button>
              </div>
            </Card>
          ) : null}

          {securityEvent ? (
            <Card className="border-rose-200 bg-rose-50/70 p-4">
              <h2 className="text-xl font-semibold tracking-tight text-rose-900">
                BLOCKED BY MODEL ARMOR
              </h2>
              <p className="mt-1 text-sm font-medium text-rose-800">{armor.title}</p>
              <ul className="mt-2 space-y-1 text-sm text-rose-900">
                <li>prompt injection / jailbreak</li>
                <li>no tool executed</li>
                <li>no records returned</li>
              </ul>
            </Card>
          ) : null}

          {showConcerning ? (
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Backup demo control
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">Simulate concerning patient response</h2>
              <p className="mt-1 text-sm text-slate-500">
                Use only if the live phone call is unavailable during recording.
              </p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm">Pain score: 8/10</div>
                <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm">Reported issue: swelling</div>
              </div>
              <div className="mt-4">
                <Button onClick={() => void runConcerning()} disabled={actionLocked}>
                  {busy === "concerning" ? "Sending…" : "Simulate concerning patient response"}
                </Button>
              </div>
            </Card>
          ) : null}

          {(preparingReview || pendingReview || awaiting === "review") && completed[5] ? (
            <Card className="border-amber-200 bg-amber-50/70 p-4">
              <h2 className="text-xl font-semibold text-amber-950">EIR escalated instead of guessing</h2>
              <p className="mt-1 text-sm leading-6 text-amber-900">
                The agent detected a concerning recovery signal and routed the case to a clinician.
              </p>
            </Card>
          ) : null}

          {pendingReview && !clinicianResolved ? (
            <Card className="border-amber-300 bg-white p-4">
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
                <Button onClick={() => void approveReview()} disabled={actionLocked}>
                  {reviewLocked ? "Review submitted — waiting for worker…" : "Approve / Mark reviewed"}
                </Button>
              </div>
            </Card>
          ) : null}

          {chain.length > 0 ? (
            <Card className="p-4">
              <h2 className="text-base font-semibold text-slate-900">Agent chain</h2>
              <p className="mt-1 text-xs text-slate-500">This episode only — not the global Observability feed.</p>
              <ol className="mt-3 space-y-0">
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

          {loopComplete ? (
            <Card className="border-emerald-300 bg-emerald-50/80 p-5">
              <h2 className="text-2xl font-semibold text-emerald-950">EIR recovery loop completed</h2>
              <ul className="mt-3 space-y-1 text-sm text-emerald-900">
                <li>
                  {pstnCheckin
                    ? "live PSTN follow-up completed"
                    : webCheckin
                      ? "in-page Gemini Live check-in completed"
                      : "recovery check-in completed"}
                </li>
                <li>medication adherence evaluated</li>
                <li>Gemini + ADK tools executed</li>
                <li>Model Armor blocked unsafe input</li>
                <li>spoken recovery signal escalated</li>
                <li>clinician reviewed the case</li>
              </ul>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button onClick={() => void startDemo()} disabled={busy === "start"}>
                  {busy === "start" ? "Starting…" : "Start new demo"}
                </Button>
                <Link
                  href={`/recovery/${episodeId}`}
                  className="inline-flex items-center rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
                >
                  Open full episode
                </Link>
                <Link
                  href="/observability"
                  className="inline-flex items-center rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
                >
                  Open observability
                </Link>
              </div>
            </Card>
          ) : null}

          {events.length > 0 ? (
            <Card className="p-4">
              <h2 className="text-base font-semibold text-slate-900">Audit timeline</h2>
              <ol className="mt-3 space-y-2">
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
        </>
      )}

      <section className="grid gap-3 sm:grid-cols-2">
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
