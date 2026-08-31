"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  CascadeWaterfall,
  HaltBanner,
  type CascadeStep,
} from "@/components/cascade/CascadeWaterfall";
import { Button, type ButtonVariant } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { APP_META, APP_ROUTES } from "@/config/app";
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
  type DemoAwait,
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
import { eventLabel, eventOutcome } from "@/lib/eventLabels";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { displayPatientId } from "@/lib/format";
import { cn } from "@/lib/cn";
import { episodeStatus, riskStatus, STATUS_VIEWS } from "@/lib/statusLabels";
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
  submitMockCheckin,
  type MockCheckinInput,
} from "@/services/api";
import type {
  AdkWorkerTelemetry,
  DomainEvent,
  HumanReview,
  PatientMedication,
  RecoveryEpisode,
  RuntimeStatus,
} from "@/types";

import type { VoiceCallState } from "../voice-preview/VoicePreviewClient";

const VoicePreviewClient = dynamic(() => import("../voice-preview/VoicePreviewClient"), {
  ssr: false,
  loading: () => <p className="text-sm text-slate-600">Loading live check-in…</p>,
});

type AwaitKind = DemoAwait;
type BusyKind =
  | "start"
  | "advance"
  | "attack"
  | "concerning"
  | "mock"
  | "review"
  | "retry"
  | null;

/** The run is four readings of one episode, not one endless column. */
const TABS = [
  { id: "run", title: "Run", hint: "sequence and cascade" },
  { id: "checkin", title: "Check-in", hint: "the call and its answers" },
  { id: "safety", title: "Safety", hint: "armor, escalation, review" },
  { id: "trace", title: "Trace", hint: "agents and audit" },
] as const;

type TabId = (typeof TABS)[number]["id"];

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
    <div className="eir-panel on-raised flex items-start gap-3 border-l-[3px] border-accent bg-raised px-5 py-4">
      <span className="eir-pulse mt-2 h-1.5 w-1.5 shrink-0 bg-accent" aria-hidden />
      <div>
        <p className="text-[1rem] font-medium text-ink">{title}</p>
        {detail ? (
          <p className="mt-1 max-w-[74ch] text-[13.5px] leading-[1.6] text-secondary">{detail}</p>
        ) : null}
      </div>
    </div>
  );
}

type TabMark = { dot?: boolean; note?: string };

/** The single "do this next" prompt, derived from the run rather than authored. */
type NextStep = {
  eyebrow: string;
  title: string;
  detail?: string;
  action?: { label: string; onClick: () => void; variant?: ButtonVariant; disabled?: boolean };
  jump?: { label: string; onClick: () => void };
  /** Set when the card is already showing what the activity banner would say. */
  fromActivity?: boolean;
};

function TabNav({
  tab,
  marks,
  onSelect,
}: {
  tab: TabId;
  marks: Record<TabId, TabMark>;
  onSelect: (id: TabId) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Demo sections"
      className="flex flex-wrap border-b border-rule-strong"
    >
      {TABS.map((item) => {
        const active = item.id === tab;
        const mark = marks[item.id];
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`demo-tab-${item.id}`}
            aria-selected={active}
            aria-controls={`demo-panel-${item.id}`}
            onClick={() => onSelect(item.id)}
            className={cn(
              "focus-ink -mb-px inline-flex min-h-11 items-center gap-2 border-b-2 px-4 text-[13.5px]",
              active
                ? "border-accent font-medium text-ink"
                : "border-transparent text-secondary hover:text-ink",
            )}
          >
            {item.title}
            {mark?.note ? (
              <span className="font-mono text-[10.5px] text-muted">{mark.note}</span>
            ) : null}
            {mark?.dot ? (
              <span className="eir-pulse h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

/**
 * One card that answers "what do I click now". Everything else on the page is
 * evidence; this is the only thing a first-time viewer has to read.
 */
function NextAction({
  eyebrow,
  title,
  detail,
  action,
  jump,
}: {
  eyebrow: string;
  title: string;
  detail?: string;
  action?: { label: string; onClick: () => void; variant?: ButtonVariant; disabled?: boolean };
  jump?: { label: string; onClick: () => void };
}) {
  return (
    <section className="eir-panel on-raised flex flex-col border-l-[3px] border-accent bg-raised px-5 py-4">
      <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-accent">
        {eyebrow}
      </span>
      <h2 className="mt-1.5 text-[1.0625rem] font-medium text-ink">{title}</h2>
      {detail ? (
        <p className="mt-1.5 max-w-[68ch] text-[13.5px] leading-[1.6] text-secondary">{detail}</p>
      ) : null}
      {action || jump ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {action ? (
            <Button
              variant={action.variant ?? "primary"}
              onClick={action.onClick}
              disabled={action.disabled}
            >
              {action.label}
              <Icon name="arrowRight" size={16} />
            </Button>
          ) : null}
          {jump ? (
            <Button variant="secondary" onClick={jump.onClick}>
              {jump.label}
            </Button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

type MockDraft = {
  painScore: number;
  reportedIssue: boolean;
  issueSummary: string;
  adherence: "yes" | "no" | "unknown";
  requestsClinician: boolean;
};

const MOCK_PRESETS: { id: string; label: string; hint: string; draft: MockDraft }[] = [
  {
    id: "concerning",
    label: "Concerning",
    hint: "escalates",
    draft: {
      painScore: 8,
      reportedIssue: true,
      issueSummary: "swelling near the incision",
      adherence: "yes",
      requestsClinician: false,
    },
  },
  {
    id: "routine",
    label: "Routine",
    hint: "no escalation",
    draft: {
      painScore: 2,
      reportedIssue: false,
      issueSummary: "",
      adherence: "yes",
      requestsClinician: false,
    },
  },
  {
    id: "missed-meds",
    label: "Missed medication",
    hint: "adherence concern",
    draft: {
      painScore: 4,
      reportedIssue: false,
      issueSummary: "",
      adherence: "no",
      requestsClinician: false,
    },
  },
];

const DEFAULT_MOCK_DRAFT = MOCK_PRESETS[0].draft;

/**
 * The spoken check-in is the real path; this types the same structured answers
 * when a demo call is hung up before EIR gathered them. It is published as
 * `synthetic: true`, so nothing downstream mistakes it for a spoken reply.
 */
function MockCheckinPanel({
  draft,
  setDraft,
  urgent,
  busy,
  disabled,
  onSubmit,
}: {
  draft: MockDraft;
  setDraft: (next: MockDraft) => void;
  urgent: boolean;
  busy: boolean;
  disabled: boolean;
  onSubmit: () => void;
}) {
  return (
    <section
      className={cn(
        "eir-panel flex flex-col border-l-[3px] px-5 py-4",
        urgent ? "on-tint border-accent bg-accent-tint" : "on-raised border-rule-strong bg-raised",
      )}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
          Mock check-in
        </span>
        <span className="font-mono text-[10.5px] text-muted">published as synthetic</span>
      </div>
      <h2 className="mt-1.5 text-[1rem] font-medium text-ink">
        {urgent
          ? "The call ended before EIR recorded any answers"
          : "Type the answers instead of speaking them"}
      </h2>
      <p className="mt-1.5 max-w-[64ch] text-[13.5px] leading-[1.6] text-secondary">
        Same event, same bus, same risk agent. The payload is flagged simulated, so the run stays
        honest about what was spoken and what was typed.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {MOCK_PRESETS.map((preset) => {
          const selected =
            draft.painScore === preset.draft.painScore &&
            draft.reportedIssue === preset.draft.reportedIssue &&
            draft.adherence === preset.draft.adherence &&
            draft.issueSummary === preset.draft.issueSummary;
          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => setDraft(preset.draft)}
              className={cn(
                "focus-ink eir-chip inline-flex min-h-9 items-center gap-2 border px-3 font-mono text-[11.5px]",
                selected
                  ? "border-accent bg-accent text-paper"
                  : "border-rule-strong text-secondary hover:border-accent hover:text-ink",
              )}
            >
              {preset.label}
              <span className={selected ? "text-paper/70" : "text-muted"}>{preset.hint}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-[136px_minmax(0,1fr)]">
        <label className="flex flex-col gap-1.5">
          <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            pain_score
          </span>
          <input
            type="number"
            min={0}
            max={10}
            value={draft.painScore}
            onChange={(event) =>
              setDraft({
                ...draft,
                painScore: Math.max(0, Math.min(10, Number(event.target.value) || 0)),
              })
            }
            className="focus-ink eir-control h-11 border border-rule-strong bg-surface px-3 font-mono text-[0.875rem] text-ink"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            issue_summary
          </span>
          <input
            type="text"
            maxLength={120}
            placeholder="e.g. swelling near the incision"
            value={draft.issueSummary}
            onChange={(event) =>
              setDraft({
                ...draft,
                issueSummary: event.target.value,
                reportedIssue: event.target.value.trim().length > 0,
              })
            }
            className="focus-ink eir-control h-11 border border-rule-strong bg-surface px-3 text-[0.875rem] text-ink"
          />
        </label>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-3">
        <label className="flex items-center gap-2.5">
          <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            medication_adherence
          </span>
          <select
            value={draft.adherence}
            onChange={(event) =>
              setDraft({ ...draft, adherence: event.target.value as MockDraft["adherence"] })
            }
            className="focus-ink eir-control h-9 border border-rule-strong bg-surface px-2 font-mono text-[0.8125rem] text-ink"
          >
            <option value="yes">yes</option>
            <option value="no">no</option>
            <option value="unknown">unknown</option>
          </select>
        </label>
        <label className="flex items-center gap-2 font-mono text-[11.5px] text-secondary">
          <input
            type="checkbox"
            checked={draft.requestsClinician}
            onChange={(event) => setDraft({ ...draft, requestsClinician: event.target.checked })}
            className="focus-ink h-4 w-4"
          />
          patient asks for a clinician
        </label>
      </div>

      <div className="mt-4 flex">
        <Button onClick={onSubmit} disabled={disabled}>
          {busy ? "Recording…" : "Send mock check-in"}
          <Icon name="arrowRight" size={16} />
        </Button>
      </div>
    </section>
  );
}

function callTimer(seconds: number): string {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function callPhaseLabel(state: VoiceCallState): string {
  if (state.status === "connecting") {
    return "Connecting…";
  }
  if (state.status === "dialing") {
    return "Dialling Gemini Live…";
  }
  if (state.phase === "hearing") {
    return "Listening to you";
  }
  if (state.phase === "thinking") {
    return "EIR is thinking";
  }
  if (state.phase === "speaking") {
    return "EIR is speaking";
  }
  return "Go ahead — EIR is listening";
}

/**
 * A call outlives whichever panel started it: the page keeps polling, sections
 * appear and reflow, and the widget can scroll far out of view. The dock is the
 * one thing that stays put — it says a call is up and can always end it.
 */
function CallDock({
  transport,
  headline,
  detail,
  timer,
  onEnd,
  onReveal,
}: {
  transport: string;
  headline: string;
  detail: string;
  timer?: string;
  onEnd?: () => void;
  onReveal?: () => void;
}) {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-4">
      <div
        role="status"
        aria-live="polite"
        className="eir-enter eir-panel on-ink pointer-events-auto flex w-full max-w-[46rem] flex-wrap items-center gap-x-5 gap-y-3 border border-accent/40 bg-ink px-5 py-3.5 shadow-[0_18px_44px_rgb(10_23_40/0.34)]"
      >
        <span className="flex min-w-0 flex-1 items-center gap-3">
          <span className="eir-pulse h-2 w-2 shrink-0 rounded-full bg-accent-bright" aria-hidden />
          <span className="flex min-w-0 flex-col">
            <span className="flex items-baseline gap-2.5">
              <span className="truncate text-[0.9375rem] font-medium text-paper">{headline}</span>
              <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-on-ink-muted">
                {transport}
              </span>
            </span>
            <span className="truncate font-mono text-[11.5px] text-on-ink-muted">{detail}</span>
          </span>
        </span>

        {timer ? (
          <span className="font-mono text-[1.125rem] leading-none tabular-nums text-paper">
            {timer}
          </span>
        ) : null}

        <span className="flex items-center gap-2">
          {onReveal ? (
            <button
              type="button"
              onClick={onReveal}
              className="focus-ink eir-control inline-flex min-h-9 items-center px-3 font-mono text-[11.5px] text-on-ink hover:text-paper"
            >
              Show check-in
            </button>
          ) : null}
          {onEnd ? (
            <Button variant="destructive" onClick={onEnd} className="min-h-9 px-4 text-[13px]">
              <Icon name="halt" size={14} />
              End call
            </Button>
          ) : null}
        </span>
      </div>
    </div>
  );
}

/**
 * The run laid out against the events' own timestamps rather than the poll
 * boundary, so the 4s/400ms fetch cadence never shows in the waterfall.
 */
function toCascade(events: DomainEvent[], halted: boolean): CascadeStep[] {
  return [...events]
    .sort((a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime())
    .map((event) => {
      const parked = halted && event.event_type === "HumanReviewRequested";
      return {
        id: event.event_id,
        label: event.event_type,
        detail: parked ? "blocking capability · parked for review" : eventOutcome(event),
        at: event.occurred_at,
        kind: EVENT_KIND[event.event_type] ?? "runtime",
        halted: parked,
        ...(parked ? { outcome: "HELD", outcomeTone: "high" as const } : {}),
      };
    });
}

function elapsedMs(events: DomainEvent[]): number {
  const times = events
    .map((event) => new Date(event.occurred_at).getTime())
    .filter((value) => !Number.isNaN(value));
  return times.length > 1 ? Math.max(...times) - Math.min(...times) : 0;
}

function formatElapsed(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  if (ms < 60_000) {
    return `${(ms / 1000).toFixed(2)}s`;
  }
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
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
  const [voiceCall, setVoiceCall] = useState<VoiceCallState | null>(null);
  const [tab, setTab] = useState<TabId>("run");
  const [mockDraft, setMockDraft] = useState<MockDraft>(DEFAULT_MOCK_DRAFT);
  const awaitingSince = useRef<number | null>(null);
  // Auto-focus a tab once per event, never again — otherwise every poll would
  // drag the viewer back off whatever they opened.
  const autoTabbed = useRef<Record<string, boolean>>({});
  // Filled by the in-page check-in widget so the dock can hang up from outside it.
  const hangupRef = useRef<(() => void) | null>(null);
  const checkinPanelRef = useRef<HTMLDivElement | null>(null);

  const onCallState = useCallback((state: VoiceCallState) => {
    // The widget reports on every tick of its call timer; only keep changes.
    setVoiceCall((prev) =>
      prev &&
      prev.status === state.status &&
      prev.phase === state.phase &&
      prev.elapsed === state.elapsed &&
      prev.audioState === state.audioState &&
      prev.micReady === state.micReady &&
      prev.micSending === state.micSending
        ? prev
        : state,
    );
  }, []);

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
        setError(getErrorMessage(err, ERROR_MESSAGES.demoRefresh));
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
    if (awaiting === "mock" && completed[3]) {
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
    setVoiceCall(null);
    hangupRef.current = null;
    setMockDraft(DEFAULT_MOCK_DRAFT);
    setTab("run");
    autoTabbed.current = {};
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
      setError(getErrorMessage(err, ERROR_MESSAGES.demoStart));
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
      setError(getErrorMessage(err, ERROR_MESSAGES.demoFastForward));
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
        setError(getErrorMessage(err, ERROR_MESSAGES.attackSimulation));
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
        setError(getErrorMessage(err, ERROR_MESSAGES.concerningSignal));
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
      await resolveReview(pendingReview.id, "Clinician reviewed demo episode.");
      beginAwait("review");
      await refresh(episodeId);
    } catch (err) {
      setBusy(null);
      setError(getErrorMessage(err, ERROR_MESSAGES.reviewResolve));
    }
  }

  async function runMockCheckin() {
    if (!episodeId) {
      return;
    }
    setBusy("mock");
    setError(null);
    const input: MockCheckinInput = {
      pain_score: mockDraft.painScore,
      reported_issue: mockDraft.reportedIssue,
      issue_summary: mockDraft.issueSummary,
      medication_adherence: mockDraft.adherence,
      patient_requests_clinician: mockDraft.requestsClinician,
    };
    try {
      await submitMockCheckin(episodeId, input);
      beginAwait("mock");
      await refresh(episodeId);
    } catch (err) {
      // A real check-in landing first is a race, not a failure.
      if (!isConflict(err)) {
        setError(getErrorMessage(err, ERROR_MESSAGES.mockCheckin));
      }
    } finally {
      setBusy(null);
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
      setError(getErrorMessage(err, ERROR_MESSAGES.voiceRetry));
    } finally {
      setBusy(null);
    }
  }

  const actionLocked = busy !== null || reviewLocked;
  const showFastForward = Boolean(episodeId) && !completed[2] && awaiting !== "follow-up";
  const voiceStarted = latestEvent(events, "VoiceCallStarted");
  // A call in this tab pins the check-in panel open. Without this the arrival of
  // a VoiceCallStarted (or of the check-in itself) unmounted the widget
  // mid-call, taking the only hang-up control with it.
  const callActive = Boolean(voiceCall?.active);
  const inPstnCall =
    !callActive &&
    isVoximplantEvent(voiceStarted) &&
    !hasEvent(events, "VoiceCallCompleted") &&
    !callFailed &&
    !completed[3];
  const webWaiting =
    callActive ||
    (Boolean(episodeId) &&
    !completed[3] &&
    !callFailed &&
    (isWebVoiceEvent(voiceStarted) ||
      (awaiting === "follow-up" &&
        Boolean(runtime?.fleet.voice?.browser_voice_enabled) &&
        !isVoximplantEvent(voiceStarted) &&
        !isScriptedVoice(voiceStarted))));
  const mockCheckin = checkin?.payload.provider === "demo-mock";
  const pstnCheckin = Boolean(checkin) && isVoximplantEvent(checkin) && !isScriptedVoice(checkin);
  const webCheckin = Boolean(checkin) && isWebVoiceEvent(checkin) && !isScriptedVoice(checkin);
  const showAttack = completed[3] && !completed[6] && awaiting !== "attack";
  const showConcerning =
    completed[3] && !concerningFromVoice && !completed[4] && awaiting !== "concerning";
  // No structured answers yet: the call was hung up early, never answered, or
  // never placed. Typed answers get the run moving again.
  const showMock =
    hasEvent(events, "FollowUpDue") && !completed[3] && !callActive && awaiting !== "mock";
  // Cleared as soon as typed answers are in flight, so the prompt does not
  // outlive the problem it describes.
  const callEndedEmpty =
    voiceCall?.status === "ended" && !completed[3] && awaiting !== "mock";
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
          setError(getErrorMessage(err, ERROR_MESSAGES.voiceOpen));
        }
      }
    }
    void prepareAlex();
    return () => {
      cancelled = true;
    };
  }, [webWaiting]);

  const dockCall = callActive || inPstnCall;
  const openCheckin = useCallback(() => {
    setTab("checkin");
    // The panel is display:none until the tab flips, so measure after paint.
    window.requestAnimationFrame(() => {
      checkinPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }, []);

  // Pull the viewer to where the action is, once per occurrence.
  useEffect(() => {
    const focus: [string, boolean, TabId][] = [
      ["call", callActive, "checkin"],
      ["review", Boolean(pendingReview) && !clinicianResolved, "safety"],
      ["armor", Boolean(securityEvent), "safety"],
    ];
    for (const [key, when, target] of focus) {
      if (when && !autoTabbed.current[key]) {
        autoTabbed.current[key] = true;
        setTab(target);
        return;
      }
    }
  }, [callActive, pendingReview, clinicianResolved, securityEvent]);

  const tabMarks: Record<TabId, TabMark> = {
    run: { note: `${completed.filter(Boolean).length}/${DEMO_STEPS.length}` },
    checkin: {
      dot: callActive || webWaiting || inPstnCall || callEndedEmpty,
      note: checkin ? "recorded" : undefined,
    },
    safety: {
      dot: (Boolean(pendingReview) && !clinicianResolved) || showAttack,
      note: securityEvent ? "blocked" : undefined,
    },
    trace: { note: events.length ? String(events.length) : undefined },
  };

  const nextAction: NextStep | null = (() => {
    if (callActive && voiceCall) {
      return {
        eyebrow: "On a call",
        title: "Recovery check-in in progress",
        detail: `${callPhaseLabel(voiceCall)}. The call bar at the bottom of the page ends it whenever you want.`,
        jump: { label: "Show the call", onClick: openCheckin },
      };
    }
    if (pendingReview && !clinicianResolved) {
      return {
        eyebrow: "Waiting on you",
        title: "The workflow is parked for a clinician",
        detail:
          "A blocking capability opened a human review and suppressed the cascade. Nothing downstream runs until this is answered.",
        action: {
          label: reviewLocked ? "Waiting for worker…" : "Resolve and resume",
          onClick: () => void approveReview(),
          disabled: actionLocked,
        },
        jump: { label: "See the parked event", onClick: () => setTab("safety") },
      };
    }
    if (callEndedEmpty) {
      return {
        eyebrow: "Nothing recorded",
        title: "The call ended before EIR gathered any answers",
        detail:
          "No recovery data was invented. Type the structured answers to carry the run forward.",
        jump: { label: "Use typed answers", onClick: openCheckin },
      };
    }
    if (activity) {
      return {
        eyebrow: "Running",
        title: activity.title,
        detail: activity.detail,
        fromActivity: true,
      };
    }
    if (showFastForward) {
      return {
        eyebrow: "Step 2",
        title: "Fast-forward to the follow-up",
        detail:
          "Demo time control only — production waits on Cloud Scheduler and claims the same idempotency key.",
        action: {
          label: busy === "advance" ? "Advancing…" : "Fast-forward to follow-up",
          onClick: () => void fastForward(),
          disabled: actionLocked,
        },
      };
    }
    if (webWaiting) {
      return {
        eyebrow: "Your turn",
        title: `Answer the check-in as ${patientName || "the patient"}`,
        detail:
          "Gemini Live is waiting in this tab. Allow the microphone and speak, or type the answers instead.",
        jump: { label: "Open the check-in", onClick: openCheckin },
      };
    }
    if (showMock) {
      return {
        eyebrow: "Your turn",
        title: "Record the recovery check-in",
        detail: "Speak it on the call, or type the same structured answers to move faster.",
        jump: { label: "Open the check-in", onClick: openCheckin },
      };
    }
    if (showAttack) {
      return {
        eyebrow: "Security",
        title: "Send the adversarial message",
        detail:
          "Model Armor screens the payload before any routing happens. No tool runs and no record is returned.",
        action: {
          label: busy === "attack" ? "Sending…" : "Simulate prompt-injection attack",
          onClick: () => void runAttack(),
          variant: "destructive" as ButtonVariant,
          disabled: actionLocked,
        },
        jump: { label: "Open safety", onClick: () => setTab("safety") },
      };
    }
    if (showConcerning) {
      return {
        eyebrow: "Backup control",
        title: "The check-in did not carry an escalation signal",
        detail:
          "Publish a concerning spoken response so the risk agent has something to assess during a recording.",
        jump: { label: "Open the check-in", onClick: openCheckin },
      };
    }
    if (loopComplete) {
      return {
        eyebrow: "Complete",
        title: "The recovery loop closed",
        detail: "Every step above came from a real handler result. Start another run when ready.",
        action: {
          label: busy === "start" ? "Starting…" : "Start new demo",
          onClick: () => void startDemo(),
          disabled: busy === "start",
        },
      };
    }
    return null;
  })();

  const cascade = toCascade(events, Boolean(pendingReview) && !clinicianResolved);
  const halted = Boolean(pendingReview) && !clinicianResolved;
  const runElapsed = elapsedMs(events);
  const suppressed = cascade.filter((step) => step.kind === "suppressed").length;

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <header className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3 border-b border-rule px-7 py-4">
        <div className="flex flex-wrap items-center gap-4">
          <Link
            href={APP_ROUTES.home}
            className="focus-ink inline-flex min-h-11 items-center gap-2.5 rounded-xl"
          >
            <span className="eir-icon-shell h-9 w-9">
              <Logo size={21} />
            </span>
            <span className="font-serif text-[1.25rem] font-semibold tracking-[-0.01em] text-ink">
              {APP_META.name}
            </span>
          </Link>
          <span className="hidden h-[15px] w-px bg-rule-strong sm:block" aria-hidden />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            Live run
          </span>
          <span className="font-mono text-[0.75rem] text-secondary">
            {episodeId
              ? `episode ${shortEpisodeId(episodeId)}${patientName ? ` · ${patientName}` : ""}`
              : "no episode open"}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-5">
          <span className="font-mono text-[0.75rem] text-secondary">
            steps <span className="text-ink">{cascade.length}</span>
          </span>
          <span className="font-mono text-[0.75rem] text-secondary">
            depth guard <span className="text-ink">12</span>
          </span>
          <span className="font-mono text-[0.75rem] text-secondary">
            elapsed <span className="text-ink">{formatElapsed(runElapsed)}</span>
          </span>
          {halted ? (
            <span className="eir-chip eir-halt inline-flex h-[26px] items-center gap-[7px] bg-ink px-2.5 font-mono text-[0.75rem] tracking-[0.08em] text-paper">
              <Icon name="halt" size={14} />
              HALTED
            </span>
          ) : null}
          <Link
            href={APP_ROUTES.login}
            className="focus-ink -my-3 inline-flex min-h-11 items-center gap-1.5 font-mono text-[11.5px] text-accent hover:text-ink"
          >
            Role portal
            <Icon name="chevronRight" size={14} />
          </Link>
        </div>
      </header>

      {/* No `items-start`: the rail is a grid item, and start-aligning it collapses
          it to its own content height so the border and the footer note stop
          mid-page. Stretching is what carries it to the bottom of the run. */}
      <div className="grid flex-grow gap-7 px-7 pb-10 pt-6 xl:grid-cols-[minmax(0,1fr)_380px] xl:gap-0 xl:px-0 xl:pt-0">
        <main className="flex min-w-0 flex-col gap-6 xl:px-7 xl:pb-6 xl:pt-6">
          <div>
            <h1 className="font-serif text-[1.625rem] font-medium leading-[1.2] tracking-[-0.015em] text-ink">
              Autonomous recovery run
            </h1>
            <p className="mt-1.5 max-w-[70ch] text-[13.5px] leading-[1.5] text-secondary">
              One follow-up, timed by the events themselves. Every step is a real handler result —
              the model never produced one. ~4 minute judge flow, demo identities only.
            </p>
          </div>

          {error ? <ErrorAlert message={error} /> : null}

          {!hydrated ? null : !episodeId ? (
            <section className="flex flex-col border-t border-rule-strong pt-5">
              <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                Consultation just ended
              </span>
              <h2 className="mt-2 font-serif text-[1.6875rem] font-medium leading-[1.2] tracking-[-0.015em] text-ink">
                Start a recovery episode
              </h2>
              <p className="mt-2 max-w-[62ch] text-[14.5px] leading-[1.55] text-secondary">
                EIR will open a Recovery Episode, schedule proactive follow-up, and wait for the
                autonomous fleet. No real patient data.
              </p>
              <div className="mt-5 flex">
                <Button onClick={() => void startDemo()} disabled={actionLocked}>
                  {busy === "start" ? "Starting…" : "Start demo"}
                  <Icon name="arrowRight" size={16} />
                </Button>
              </div>
            </section>
          ) : (
            <>
              {nextAction ? (
                <NextAction
                  eyebrow={nextAction.eyebrow}
                  title={nextAction.title}
                  detail={nextAction.detail}
                  action={nextAction.action}
                  jump={nextAction.jump}
                />
              ) : null}

              {activity && !nextAction?.fromActivity ? (
                <ActivityBanner title={activity.title} detail={activity.detail} />
              ) : null}

              {stalled ? (
                <p className="eir-panel border-l-[3px] border-warn bg-warn-tint px-4 py-3 text-[13.5px] text-warn">
                  Still processing — check Observability.
                </p>
              ) : null}

              <TabNav tab={tab} marks={tabMarks} onSelect={setTab} />

              <div
                role="tabpanel"
                id="demo-panel-run"
                aria-labelledby="demo-tab-run"
                aria-label="Run"
                style={{ display: tab === "run" ? undefined : "none" }}
                className="flex flex-col gap-6"
              >
                {/* the run, as a ledger */}
                <section className="flex flex-col">
                  <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                    <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                      Demo sequence
                    </h2>
                    <span className="font-mono text-[10.5px] text-muted">
                      {completed.filter(Boolean).length} of {DEMO_STEPS.length} recorded
                    </span>
                  </div>
                  <ol>
                    {DEMO_STEPS.map((step, index) => {
                      const done = completed[index];
                      const current = index === stepIndex && !completed.every(Boolean);
                      return (
                        <li
                          key={step.id}
                          className={cn(
                            "grid min-h-11 grid-cols-[34px_minmax(0,1fr)_92px] items-center gap-4 border-b border-rule",
                            current &&
                              "on-raised bg-raised pl-2.5 shadow-[inset_3px_0_0_0_var(--color-accent)]",
                          )}
                        >
                          <span className="font-mono text-[10.5px] text-muted">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span
                            className={cn(
                              "truncate font-mono text-[12.5px]",
                              done ? "text-ink" : current ? "font-medium text-ink" : "text-inactive",
                            )}
                          >
                            {step.title}
                          </span>
                          <span
                            className={cn(
                              "text-right font-mono text-[11.5px]",
                              done ? "text-ok" : current ? "text-accent" : "text-inactive",
                            )}
                          >
                            {done ? "done" : current ? "running" : "queued"}
                          </span>
                        </li>
                      );
                    })}
                  </ol>
                </section>

                {/* the cascade itself, laid against event timestamps */}
                {cascade.length ? (
                  <section className="flex min-w-0 flex-col gap-5">
                    <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                      <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                        Event cascade
                      </h2>
                      <span className="font-mono text-[10.5px] text-muted">
                        drawn against event timestamps, not the poll
                      </span>
                    </div>
                    <CascadeWaterfall steps={cascade} />
                    {halted ? (
                      <HaltBanner
                        title={`CASCADE HALTED AT ${formatElapsed(runElapsed)}`}
                        detail={
                          suppressed
                            ? `${suppressed} downstream event${suppressed === 1 ? " was" : "s were"} suppressed. The workflow resumes only when a clinician answers.`
                            : "The workflow is parked on a blocking capability. It resumes only when a clinician answers."
                        }
                      />
                    ) : null}
                  </section>
                ) : null}

                {showFastForward ? (
                  <section className="flex flex-col border-t border-rule-strong pt-4">
                    <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                      Time control
                    </h2>
                    <p className="mt-2 max-w-[62ch] text-[0.875rem] leading-[1.55] text-secondary">
                      Demo time control only — production waits on Cloud Scheduler.
                    </p>
                    <div className="mt-4 flex">
                      <Button onClick={() => void fastForward()} disabled={actionLocked}>
                        {busy === "advance" ? "Advancing…" : "Fast-forward to follow-up"}
                        <Icon name="arrowRight" size={16} />
                      </Button>
                    </div>
                  </section>
                ) : null}

                {loopComplete ? (
                  <section className="flex flex-col border-t border-rule-strong pt-5">
                    <h2 className="font-serif text-[1.6875rem] font-medium leading-[1.2] tracking-[-0.015em] text-ink">
                      Recovery loop completed
                    </h2>
                    <ol className="mt-4">
                      {[
                        pstnCheckin
                          ? "live PSTN follow-up completed"
                          : webCheckin
                            ? "in-page Gemini Live check-in completed"
                            : mockCheckin
                              ? "typed recovery check-in recorded"
                              : "recovery check-in completed",
                        "medication adherence evaluated",
                        "Gemini + ADK tools executed",
                        "Model Armor blocked unsafe input",
                        "spoken recovery signal escalated",
                        "clinician reviewed the case",
                      ].map((line, index) => (
                        <li
                          key={line}
                          className="grid min-h-10 grid-cols-[34px_minmax(0,1fr)] items-center gap-4 border-b border-rule"
                        >
                          <span className="font-mono text-[10.5px] text-muted">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span className="text-[0.875rem] text-secondary">{line}</span>
                        </li>
                      ))}
                    </ol>
                    <div className="mt-5 flex flex-wrap gap-2">
                      <Button onClick={() => void startDemo()} disabled={busy === "start"}>
                        {busy === "start" ? "Starting…" : "Start new demo"}
                        <Icon name="arrowRight" size={16} />
                      </Button>
                      <Link
                        href={`/recovery/${episodeId}`}
                        className="focus-ink inline-flex min-h-11 items-center gap-2.5 border border-rule-strong px-5 text-sm font-medium text-body hover:bg-hover"
                      >
                        Open full episode
                        <Icon name="open" size={16} />
                      </Link>
                      <Link
                        href="/observability"
                        className="focus-ink inline-flex min-h-11 items-center gap-2.5 border border-rule-strong px-5 text-sm font-medium text-body hover:bg-hover"
                      >
                        Open observability
                        <Icon name="open" size={16} />
                      </Link>
                    </div>
                  </section>
                ) : null}
              </div>

              <div
                ref={checkinPanelRef}
                role="tabpanel"
                id="demo-panel-checkin"
                aria-labelledby="demo-tab-checkin"
                aria-label="Check-in"
                style={{ display: tab === "checkin" ? undefined : "none" }}
                className="flex flex-col gap-6"
              >
                {inPstnCall ? (
                  <section
                    className="eir-panel on-raised flex flex-col border-l-[3px] border-accent bg-raised px-5 py-4"
                  >
                    <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                      Real voice outreach
                    </span>
                    <h2 className="mt-1.5 text-[1rem] font-medium text-ink">
                      {hasEvent(events, "VoiceCallConnected")
                        ? "Gemini Live conversation active"
                        : "Calling patient…"}
                    </h2>
                    <dl className="mt-3 grid grid-cols-[128px_minmax(0,1fr)] gap-x-3.5 gap-y-2 font-mono text-[0.75rem]">
                      <dt className="text-muted">transport</dt>
                      <dd className="text-body">voximplant · pstn</dd>
                      <dt className="text-muted">model</dt>
                      <dd className="truncate text-body">
                        {runtime?.fleet.voice?.gemini_live_model ||
                          "gemini-live-2.5-flash-native-audio"}
                      </dd>
                      <dt className="text-muted">identity</dt>
                      <dd className="text-body">demo patient · real phone call</dd>
                    </dl>
                  </section>
                ) : null}

                {webWaiting ? (
                  <section
                    className="eir-panel on-tint flex flex-col border-l-[3px] border-accent bg-accent-tint px-5 py-4"
                  >
                    <span className="flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.1em] text-accent">
                      {callActive ? (
                        <span className="eir-pulse h-1.5 w-1.5 shrink-0 bg-accent" aria-hidden />
                      ) : null}
                      {callActive ? "Check-in in progress" : "Live Gemini check-in"}
                    </span>
                    <h2 className="mt-1.5 text-[1rem] font-medium text-ink">
                      {callActive
                        ? `On a live check-in with ${patientName || "the patient"}`
                        : `Answer as ${patientName || "the patient"} in this tab`}
                    </h2>
                    <p className="mt-1.5 max-w-[62ch] text-[13.5px] leading-[1.6] text-secondary">
                      {callActive
                        ? "The call bar at the bottom of the page stays with you — it shows what the agent is doing and ends the call whenever you want."
                        : "WebRTC to Gemini Live — close any other Voximplant softphone first. Say your pain level, symptoms, and whether you took your medications."}
                    </p>
                    <div className="mt-4">
                      {alexReady && episodeId ? (
                        <VoicePreviewClient
                          episodeId={episodeId}
                          compact
                          onCallState={onCallState}
                          hangupRef={hangupRef}
                        />
                      ) : (
                        <p className="font-mono text-[11.5px] text-muted">
                          Preparing the in-page check-in…
                        </p>
                      )}
                    </div>
                  </section>
                ) : null}

                {showMock ? (
                  <MockCheckinPanel
                    draft={mockDraft}
                    setDraft={setMockDraft}
                    urgent={Boolean(callEndedEmpty)}
                    busy={busy === "mock"}
                    disabled={actionLocked}
                    onSubmit={() => void runMockCheckin()}
                  />
                ) : null}

                {checkin ? (
                  <section className="flex flex-col">
                    <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                      <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                        Recovery check-in received
                      </h2>
                      <span className="font-mono text-[10.5px] text-muted">
                        {pstnCheckin
                          ? "real phone follow-up"
                          : webCheckin
                            ? "in-page Gemini Live"
                            : mockCheckin
                              ? "typed, not spoken"
                              : "scripted voice"}
                      </span>
                    </div>
                    <dl className="grid grid-cols-[168px_minmax(0,1fr)] gap-x-5 gap-y-2 py-4 font-mono text-[0.8125rem]">
                      <dt className="text-muted">pain_score</dt>
                      <dd className="text-ink">{String(checkin.payload.pain_score ?? "—")}/10</dd>
                      <dt className="text-muted">reported_issue</dt>
                      <dd className="text-ink">
                        {checkin.payload.reported_issue
                          ? String(checkin.payload.issue_summary || "yes")
                          : "none"}
                      </dd>
                      <dt className="text-muted">medication_adherence</dt>
                      <dd className="text-ink">
                        {String(checkin.payload.medication_adherence ?? "unknown")}
                      </dd>
                      <dt className="text-muted">provider</dt>
                      <dd className="text-ink">{String(checkin.payload.provider ?? "voice")}</dd>
                    </dl>
                  </section>
                ) : null}

                {medications.length ? (
                  <section className="flex flex-col">
                    <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                      <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                        Prescribed medications
                      </h2>
                      <span className="font-mono text-[10.5px] text-muted">
                        {medications.length} on file
                      </span>
                    </div>
                    <p className="max-w-[70ch] py-3 text-[13.5px] leading-[1.6] text-secondary">
                      The same catalog the replenishment fleet uses. Gemini asks whether medications
                      were taken; the names are matched on the server after the check-in.
                    </p>
                    <ul className="flex flex-col">
                      {medications.map((medication) => (
                        <li
                          key={medication.sku || medication.rxnorm_code || medication.name}
                          className="grid min-h-11 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-rule py-2"
                        >
                          <span className="flex min-w-0 flex-col gap-0.5">
                            <span className="truncate text-[0.875rem] text-ink">
                              {medication.name}
                            </span>
                            <span className="truncate font-mono text-[11.5px] text-muted">
                              {[medication.dose, medication.sku].filter(Boolean).join(" · ") ||
                                "no dose recorded"}
                            </span>
                          </span>
                          {medication.critical ? (
                            <StatusBadge status={STATUS_VIEWS.criticalMedication} />
                          ) : (
                            <span className="font-mono text-[11.5px] text-inactive">routine</span>
                          )}
                        </li>
                      ))}
                    </ul>
                    {checkin ? (
                      <p className="pt-3 text-[13.5px] leading-[1.6] text-secondary">
                        Latest adherence{" "}
                        <span className="font-medium text-ink">
                          {String(checkin.payload.medication_adherence ?? "unknown")}
                        </span>
                        {adherenceEvent ? " · the adherence agent flagged this episode" : ""}
                      </p>
                    ) : null}
                  </section>
                ) : null}

                {callFailed ? (
                  <section className="eir-panel flex flex-col border-l-[3px] border-warn bg-warn-tint px-5 py-4">
                    <h2 className="text-[1rem] font-medium text-ink">
                      Voice outreach did not complete
                    </h2>
                    <p className="mt-1.5 max-w-[62ch] text-[13.5px] leading-[1.6] text-secondary">
                      No recovery data was invented. One manual retry is available.
                    </p>
                    <div className="mt-4 flex">
                      <Button
                        variant="secondary"
                        onClick={() => void retryVoice()}
                        disabled={actionLocked}
                      >
                        {busy === "retry" ? "Retrying…" : "Retry voice outreach once"}
                      </Button>
                    </div>
                  </section>
                ) : null}

                {showConcerning ? (
                  <section className="flex flex-col border-t border-rule-strong pt-4">
                    <div className="flex items-baseline justify-between gap-4">
                      <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                        Backup demo control
                      </h2>
                      <span className="font-mono text-[10.5px] text-muted">
                        only if the live call is unavailable
                      </span>
                    </div>
                    <p className="mt-2 max-w-[62ch] text-[0.875rem] leading-[1.55] text-secondary">
                      Simulates a concerning spoken response so the risk agent has something to assess
                      during a recording.
                    </p>
                    <dl className="mt-3 grid grid-cols-[168px_minmax(0,1fr)] gap-x-5 gap-y-2 font-mono text-[0.8125rem]">
                      <dt className="text-muted">pain_score</dt>
                      <dd className="text-ink">8/10</dd>
                      <dt className="text-muted">reported_issue</dt>
                      <dd className="text-ink">swelling</dd>
                    </dl>
                    <div className="mt-4 flex">
                      <Button onClick={() => void runConcerning()} disabled={actionLocked}>
                        {busy === "concerning" ? "Sending…" : "Simulate concerning response"}
                      </Button>
                    </div>
                  </section>
                ) : null}
              </div>

              <div
                role="tabpanel"
                id="demo-panel-safety"
                aria-labelledby="demo-tab-safety"
                aria-label="Safety"
                style={{ display: tab === "safety" ? undefined : "none" }}
                className="flex flex-col gap-6"
              >
                {showAttack ? (
                  <section className="flex flex-col border-t border-rule-strong pt-4">
                    <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                      Adversarial input
                    </h2>
                    <p className="eir-panel mt-3 border-l-[3px] border-rule-strong bg-raised px-4 py-3 font-mono text-[0.8125rem] text-body">
                      {DEMO_ATTACK_PROMPT}
                    </p>
                    <div className="mt-4 flex">
                      <Button
                        variant="destructive"
                        onClick={() => void runAttack()}
                        disabled={actionLocked}
                      >
                        {busy === "attack" ? "Sending…" : "Simulate prompt-injection attack"}
                      </Button>
                    </div>
                  </section>
                ) : null}

                {securityEvent ? (
                  <section className="eir-panel eir-halt on-ink flex flex-col border-l-[3px] border-high bg-ink px-5 py-4">
                    <span className="inline-flex items-center gap-2 font-mono text-[0.75rem] font-medium tracking-[0.12em] text-paper">
                      <Icon name="halt" size={14} />
                      BLOCKED BY MODEL ARMOR
                    </span>
                    <p className="mt-2 font-mono text-[12.5px] text-on-ink">{armor.title}</p>
                    <dl className="mt-3 grid grid-cols-[148px_minmax(0,1fr)] gap-x-5 gap-y-2 font-mono text-[0.75rem]">
                      <dt className="text-on-ink-muted">classification</dt>
                      <dd className="text-paper">prompt injection / jailbreak</dd>
                      <dt className="text-on-ink-muted">tools executed</dt>
                      <dd className="text-paper">none</dd>
                      <dt className="text-on-ink-muted">records returned</dt>
                      <dd className="text-paper">none</dd>
                      <dt className="text-on-ink-muted">adapter</dt>
                      <dd className={armor.managed ? "text-paper" : "text-warn"}>
                        {armor.managed ? "managed" : "fallback"}
                      </dd>
                    </dl>
                  </section>
                ) : null}

                {(preparingReview || pendingReview || awaiting === "review") && completed[5] ? (
                  <p className="eir-panel border-l-[3px] border-accent bg-raised px-5 py-4 text-[0.875rem] leading-[1.6] text-secondary">
                    <span className="font-medium text-ink">EIR escalated instead of guessing.</span>{" "}
                    The agent detected a concerning recovery signal and routed the case to a clinician
                    rather than acting on it.
                  </p>
                ) : null}

                {pendingReview && !clinicianResolved ? (
                  <section className="flex flex-col">
                    <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                      <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                        Parked event
                      </h2>
                      <span className="font-mono text-[10.5px] text-muted">
                        replayed verbatim on resume
                      </span>
                    </div>
                    <dl className="grid grid-cols-[168px_minmax(0,1fr)] gap-x-5 gap-y-2 py-4 font-mono text-[0.8125rem]">
                      <dt className="text-muted">reason</dt>
                      <dd className="text-ink">{pendingReview.reason}</dd>
                      <dt className="text-muted">requested_by</dt>
                      <dd className="text-ink">{pendingReview.agent_name}</dd>
                      <dt className="text-muted">pending_capability</dt>
                      <dd className="text-ink">
                        {pendingReview.pending_capability || pendingReview.capability || "—"}
                      </dd>
                      <dt className="text-muted">review_status</dt>
                      <dd className="text-ink">{pendingReview.status.toUpperCase()}</dd>
                      <dt className="text-muted">episode_risk</dt>
                      <dd className="text-ink">{episode?.risk_level ?? "—"}</dd>
                      <dt className="text-muted">requested_at</dt>
                      <dd className="text-ink">{formatWhen(pendingReview.created_at)}</dd>
                    </dl>
                    <div className="flex">
                      <Button onClick={() => void approveReview()} disabled={actionLocked}>
                        {reviewLocked ? "Waiting for worker…" : "Resolve and resume"}
                        <Icon name="approve" size={16} />
                      </Button>
                    </div>
                  </section>
                ) : null}
              </div>

              <div
                role="tabpanel"
                id="demo-panel-trace"
                aria-labelledby="demo-tab-trace"
                aria-label="Trace"
                style={{ display: tab === "trace" ? undefined : "none" }}
                className="flex flex-col gap-6"
              >
                {chain.length > 0 ? (
                  <section className="flex flex-col">
                    <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                      <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                        Agent chain
                      </h2>
                      <span className="font-mono text-[10.5px] text-muted">this episode only</span>
                    </div>
                    <ol>
                      {chain.map((item, index) => (
                        <li
                          key={`${item.timestamp}-${item.agent_name}-${index}`}
                          className="grid min-h-11 grid-cols-[34px_minmax(0,1fr)_minmax(0,1fr)] items-center gap-4 border-b border-rule"
                        >
                          <span className="font-mono text-[10.5px] text-muted">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span className="truncate font-mono text-[12.5px] text-ink">
                            {item.agent_name}
                          </span>
                          <span className="truncate font-mono text-[11.5px] text-muted">
                            {chainToolLabel(item)}
                          </span>
                        </li>
                      ))}
                    </ol>
                  </section>
                ) : null}

                {events.length > 0 ? (
                  <section className="flex flex-col">
                    <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                      <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                        Audit timeline
                      </h2>
                      <span className="font-mono text-[10.5px] text-muted">
                        {events.length} event{events.length === 1 ? "" : "s"}
                      </span>
                    </div>
                    <ol>
                      {events.map((event) => (
                        <li
                          key={event.event_id}
                          className="grid min-h-11 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-rule"
                        >
                          <div className="flex min-w-0 flex-col gap-0.5">
                            <span className="truncate text-[0.875rem] text-ink">
                              {eventLabel(event.event_type).title}
                            </span>
                            <span className="truncate font-mono text-[0.75rem] text-muted">
                              {event.event_type}
                            </span>
                          </div>
                          <span className="font-mono text-[11.5px] text-muted">
                            {formatWhen(event.occurred_at)}
                          </span>
                        </li>
                      ))}
                    </ol>
                  </section>
                ) : null}
              </div>
            </>
          )}
        </main>

        <aside className="on-raised flex flex-col border-t border-rule bg-raised xl:border-l xl:border-t-0">
          {episodeId ? (
            <div className="flex flex-col gap-2 border-b border-rule px-6 pb-4 pt-5">
              <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                Episode
              </span>
              <h2 className="font-mono text-[1.0625rem] font-medium text-ink">
                {patientName || "Demo patient"}
              </h2>
              <span className="font-mono text-[11.5px] text-muted">
                {shortEpisodeId(episodeId)}
                {episode?.patient_id ? ` · ${displayPatientId(episode.patient_id)}` : ""}
              </span>
              {episode ? (
                <div className="mt-1 flex flex-wrap gap-2">
                  <StatusBadge status={episodeStatus(episode.status)} />
                  <StatusBadge status={riskStatus(episode.risk_level)} />
                </div>
              ) : null}
            </div>
          ) : null}

          {episode ? (
            <div className="flex flex-col gap-2.5 border-b border-rule px-6 py-4">
              <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                Schedule
              </span>
              <dl className="grid grid-cols-[104px_minmax(0,1fr)] gap-x-3.5 gap-y-2 font-mono text-[0.75rem]">
                <dt className="text-muted">started</dt>
                <dd className="text-body">{formatWhen(episode.started_at)}</dd>
                <dt className="text-muted">next follow-up</dt>
                <dd className="text-body">{formatWhen(episode.next_follow_up_at)}</dd>
                <dt className="text-muted">assigned</dt>
                <dd className="text-body">{episode.assigned_agents.join(", ") || "none"}</dd>
              </dl>
            </div>
          ) : null}

          {proof.length ? (
            <div className="flex flex-col gap-2.5 border-b border-rule px-6 py-4">
              <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
                Runtime proof
              </span>
              <dl className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3.5 gap-y-2 font-mono text-[0.75rem]">
                {proof.map((row) => (
                  <div key={row.label} className="contents">
                    <dt className="truncate text-muted">{row.label}</dt>
                    <dd
                      className={cn(
                        "text-right tracking-[0.06em]",
                        row.live ? "text-ok" : "text-warn",
                      )}
                    >
                      {row.value}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}

          <div className="flex flex-col gap-2.5 border-b border-rule px-6 py-4">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
              Why it holds
            </span>
            <ol>
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
              ].map((item, index) => (
                <li
                  key={item.title}
                  className="grid grid-cols-[26px_minmax(0,1fr)] gap-3 border-b border-rule py-3 last:border-b-0"
                >
                  <span className="font-mono text-[10.5px] text-muted">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="flex flex-col gap-1">
                    <span className="font-mono text-[0.75rem] text-ink">{item.title}</span>
                    <span className="text-[12.5px] leading-[1.55] text-secondary">{item.body}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>

          <div className="mt-auto flex flex-col gap-2 border-t border-rule-strong px-6 pb-5 pt-4">
            <span className="font-mono text-[10.5px] leading-[1.55] text-muted">
              Handler results come from Python, never from the model.
            </span>
            <span className="font-mono text-[10.5px] leading-[1.55] text-muted">
              Demo environment · no real patient data
            </span>
          </div>
        </aside>
      </div>

      {/* Clears the fixed dock so it never sits on top of the last row. */}
      {dockCall ? <div className="h-24 shrink-0" aria-hidden /> : null}

      {callActive && voiceCall ? (
        <CallDock
          transport="webrtc · in-page"
          headline={
            voiceCall.live
              ? `Live check-in · ${patientName || "patient"}`
              : "Starting the check-in…"
          }
          detail={`${callPhaseLabel(voiceCall)}${
            voiceCall.audioState === "blocked" ? " · tap Unlock sound in the panel" : ""
          }`}
          timer={voiceCall.live ? callTimer(voiceCall.elapsed) : undefined}
          onEnd={() => hangupRef.current?.()}
          onReveal={openCheckin}
        />
      ) : null}

      {inPstnCall ? (
        <CallDock
          transport="voximplant · pstn"
          headline={
            hasEvent(events, "VoiceCallConnected")
              ? "Gemini Live conversation active"
              : "Calling the patient…"
          }
          detail="Real outbound phone call — it ends when the patient hangs up."
          onReveal={openCheckin}
        />
      ) : null}
    </div>
  );
}
