"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  CascadeWaterfall,
  HaltBanner,
  type CascadeStep,
} from "@/components/cascade/CascadeWaterfall";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
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
} from "@/lib/demoStory";
import { eventLabel } from "@/lib/eventLabels";
import { cn } from "@/lib/cn";
import { episodeBadgeClass, riskBadgeClass } from "@/lib/status";
import {
  advanceDemoFollowUp,
  bootstrapDemo,
  getRecovery,
  getRuntimeHistory,
  getRuntimeStatus,
  listRecoveryEvents,
  listReviews,
  resolveReview,
  simulateConcerningSignal,
  simulatePromptInjection,
  retryDemoVoice,
} from "@/services/api";
import type {
  AdkWorkerTelemetry,
  DomainEvent,
  HumanReview,
  RecoveryEpisode,
  RuntimeStatus,
} from "@/types";

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

/** Events the runtime raises, versus work an agent did, versus a call out of process. */
const EVENT_KIND: Record<string, CascadeStep["kind"]> = {
  RecoveryEpisodeStarted: "runtime",
  FollowUpDue: "runtime",
  PatientResponded: "runtime",
  VoiceCallStarted: "external",
  VoiceCallConnected: "external",
  VoiceCallCompleted: "external",
  VoiceCallFailed: "external",
  RiskEscalated: "agent",
  AdherenceConcernDetected: "agent",
  HumanReviewRequested: "agent",
  ClinicianResolved: "agent",
  ContentSecurityBlocked: "suppressed",
};

function ActivityBanner({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="on-raised flex items-start gap-3 border-l-[3px] border-accent bg-raised px-5 py-4">
      <span className="eir-pulse mt-2 h-1.5 w-1.5 shrink-0 bg-accent" aria-hidden />
      <div>
        <p className="text-[16px] font-medium text-ink">{title}</p>
        {detail ? (
          <p className="mt-1 max-w-[74ch] text-[13.5px] leading-[1.6] text-secondary">{detail}</p>
        ) : null}
      </div>
    </div>
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
  const inCall =
    isVoximplantEvent(voiceStarted) &&
    !hasEvent(events, "VoiceCallCompleted") &&
    !callFailed;
  const pstnCheckin = Boolean(checkin) && isVoximplantEvent(checkin) && !isScriptedVoice(checkin);
  const showAttack = completed[3] && !completed[6] && awaiting !== "attack";
  const showConcerning =
    (callFailed || (completed[3] && !concerningFromVoice)) &&
    !completed[4] &&
    awaiting !== "concerning";

