"use client";

import { useEffect, useRef, useState } from "react";
import type * as VoxSdk from "voximplant-websdk";

import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { clearSession, loadSession } from "@/lib/auth";
import { VOX_PREVIEW_NODE } from "@/lib/voximplantPreview";
import { appendTranscript, type TranscriptLine, type TranscriptRole } from "@/lib/voiceTranscript";
import {
  getCurrentUser,
  getVoiceWebConfig,
  listRecovery,
  startVoiceWebSession,
  type CurrentUser,
  type VoiceWebConfig,
} from "@/services/api";

type Status = "idle" | "connecting" | "dialing" | "in_call" | "ended";
type AudioState = "idle" | "waiting" | "playing" | "blocked";
/** What the conversation is doing right now, from the patient's point of view. */
type Phase = "idle" | "listening" | "hearing" | "thinking" | "speaking";

// Local mic thresholds. Speech has to clear VOICE_ON to register, then stay
// under it for VOICE_OFF_MS before the turn counts as over -- without that
// hysteresis the indicator strobes on every syllable gap.
const VOICE_ON = 0.025;
const VOICE_OFF_MS = 260;

type PreviewRenderer = {
  kind?: string;
  stream?: MediaStream;
  element?: HTMLMediaElement;
  enable: () => void;
  render: (container?: HTMLElement) => void;
};

type PreviewEndpoint = {
  mediaRenderers?: PreviewRenderer[];
  on: (event: unknown, handler: (payload: unknown) => void) => void;
};

type PreviewCall = {
  hangup: () => void;
  unmutePlayback: () => void;
  getEndpoints: () => PreviewEndpoint[];
  on: (event: unknown, handler: (payload: unknown) => void) => void;
  peerConnection?: { peerConnection?: RTCPeerConnection };
};

const voiceDebug = {
  info: (...args: unknown[]) =>
    process.env.NODE_ENV === "development" ? console.info("[eir-voice]", ...args) : undefined,
  warn: (...args: unknown[]) =>
    process.env.NODE_ENV === "development" ? console.warn("[eir-voice]", ...args) : undefined,
  error: (...args: unknown[]) =>
    process.env.NODE_ENV === "development" ? console.error("[eir-voice]", ...args) : undefined,
};

const VOX_AUTH_CODES: Record<number, string> = {
  401: "Voximplant rejected the login signature (invalid password or one-time key hash)",
  403: "The Voximplant account is frozen",
  404: "The Voximplant user does not exist",
  500: "Voximplant had an internal error",
};

function describeVoxAuthCode(code: unknown): string | null {
  return typeof code === "number" ? (VOX_AUTH_CODES[code] ?? null) : null;
}

function describeError(err: unknown): string {
  if (err instanceof Error && err.message) {
    return err.message;
  }
  if (typeof err === "string" && err.trim()) {
    return err;
  }
  if (err && typeof err === "object") {
    const rec = err as { message?: unknown; code?: unknown };
    const known = describeVoxAuthCode(rec.code);
    if (known) {
      return `${known} (code ${String(rec.code)})`;
    }
    return [rec.message, rec.code].filter(Boolean).map(String).join(" ") || "Could not connect";
  }
  return "Could not connect to Voximplant";
}

async function loadVoxSdk(): Promise<typeof VoxSdk> {
  const mod = await import("voximplant-websdk");
  const fromModule = (mod as { getInstance?: unknown }).getInstance
    ? mod
    : (mod as { default?: typeof VoxSdk }).default;
  if (fromModule && typeof fromModule.getInstance === "function") {
    return fromModule;
  }
  const fromWindow = (window as unknown as { VoxImplant?: typeof VoxSdk }).VoxImplant;
  if (fromWindow && typeof fromWindow.getInstance === "function") {
    return fromWindow;
  }
  throw new Error("Voximplant SDK failed to load in the browser");
}

function formatTimer(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function statusLabel(status: Status): string {
  if (status === "in_call") {
    return "Connected";
  }
  if (status === "dialing") {
    return "Calling EIR…";
  }
  if (status === "connecting") {
    return "Connecting…";
  }
  if (status === "ended") {
    return "Check-in ended";
  }
  return "Ready to start";
}

function phaseLabel(phase: Phase): string {
  if (phase === "hearing") {
    return "Listening to you…";
  }
  if (phase === "thinking") {
    return "EIR is thinking…";
  }
  if (phase === "speaking") {
    return "EIR is speaking";
  }
  if (phase === "listening") {
    return "Go ahead — EIR is listening";
  }
  return "Not connected";
}

function audioLabel(state: AudioState): string {
  if (state === "playing") {
    return "Remote audio active";
  }
  if (state === "waiting") {
    return "Waiting for remote audio";
  }
  if (state === "blocked") {
    return "Tap to unlock sound";
  }
  return "Audio idle";
}

export default function VoicePreviewClient() {
  const sdkRef = useRef<ReturnType<typeof VoxSdk.getInstance> | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const eventsRef = useRef<typeof VoxSdk | null>(null);
  const callRef = useRef<PreviewCall | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const remoteBytesRef = useRef(0);
  const micBytesRef = useRef(0);
  const routedStreams = useRef(new WeakSet<MediaStream>());
  const wiredEndpoints = useRef(new WeakSet<object>());
  const micHandlerSet = useRef(false);
  const meterRef = useRef<HTMLDivElement | null>(null);
  const meterFrameRef = useRef<number | null>(null);
  const meterSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const voiceSinceRef = useRef(0);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [micReady, setMicReady] = useState(false);
  const [micSending, setMicSending] = useState(false);
  const [micSpeaking, setMicSpeaking] = useState(false);
  const [awaitingReply, setAwaitingReply] = useState(false);
  const [audioState, setAudioState] = useState<AudioState>("idle");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [episodeId, setEpisodeId] = useState<string | null>(null);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [config, setConfig] = useState<VoiceWebConfig | null>(null);
  const [session, setSession] = useState<CurrentUser | null>(null);
  const [loadingEpisode, setLoadingEpisode] = useState(true);
  const signedInAsPatient = Boolean(session?.role === "PATIENT" && session?.patient_id);

  useEffect(() => {
    if (status !== "in_call") {
      return undefined;
    }
    setElapsed(0);
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [lines]);

  useEffect(() => stopMicMeter, []);

  // Resolve where to dial and which episode this patient is checking in on.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      const stored = loadSession();
      try {
        const [webConfig, me, episodes] = await Promise.all([
          getVoiceWebConfig(),
          getCurrentUser(),
          listRecovery(),
        ]);
        if (cancelled) {
          return;
        }
        setConfig(webConfig);
        if (!me) {
          // Absent, expired, or rejected. Drop the stale session so the page
          // stops offering a check-in that can only 401 on click.
          if (stored) {
            clearSession();
          }
          setSession(null);
          setEpisodeId(null);
          return;
        }
        setSession(me);
        // Never fall back to someone else's episode: the server rejects it with
        // a 403, and offering it at all is the wrong affordance.
        const patientId = me.role === "PATIENT" ? me.patient_id : null;
        const mine = patientId
          ? episodes.filter((episode) => episode.patient_id === patientId)
          : [];
        const active = mine.find((episode) => episode.status === "ACTIVE") ?? mine[0];
        setEpisodeId(active?.id ?? null);
      } catch (err) {
        if (!cancelled) {
          setError(describeError(err));
        }
      } finally {
        if (!cancelled) {
          setLoadingEpisode(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  function getAudioContextCtor(): typeof AudioContext {
    const Ctor =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) {
      throw new Error("This browser cannot play WebRTC audio");
    }
    return Ctor;
  }

  async function resumeAudioContext(): Promise<AudioContext> {
    const Ctor = getAudioContextCtor();
    const ctx = ctxRef.current ?? new Ctor();
    ctxRef.current = ctx;
    if (ctx.state === "suspended") {
      await ctx.resume();
    }
    return ctx;
  }

  function stopMicMeter() {
    if (meterFrameRef.current !== null) {
      cancelAnimationFrame(meterFrameRef.current);
      meterFrameRef.current = null;
    }
    meterSourceRef.current?.disconnect();
    meterSourceRef.current = null;
    voiceSinceRef.current = 0;
    setMicSpeaking(false);
    if (meterRef.current) {
      meterRef.current.style.transform = "scaleX(0)";
    }
  }

  /**
   * Level meter on the audio actually being sent, taken from the outbound RTC
   * track rather than a second getUserMedia so there is no competing capture.
   * This is the only "we can hear you" signal that costs no round trip: the
   * transcript can only confirm it after Gemini has transcribed the audio.
   */
  function startMicMeter(call: PreviewCall) {
    const ctx = ctxRef.current;
    const pc = getRawPeerConnection(call);
    if (!ctx || !pc || meterSourceRef.current) {
      return;
    }
    const track = pc.getSenders().find((sender) => sender.track?.kind === "audio")?.track;
    if (!track) {
      voiceDebug.warn("no outbound audio track to meter");
      return;
    }
    let source: MediaStreamAudioSourceNode;
    let analyser: AnalyserNode;
    try {
      source = ctx.createMediaStreamSource(new MediaStream([track]));
      analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.6;
      // Deliberately not connected to ctx.destination: this only measures the
      // mic, and routing it to the speakers would play the patient back to
      // themselves.
      source.connect(analyser);
    } catch (err) {
      voiceDebug.warn("mic meter unavailable", err);
      return;
    }
    meterSourceRef.current = source;
    const samples = new Float32Array(analyser.fftSize);

    const tick = () => {
      meterFrameRef.current = requestAnimationFrame(tick);
      analyser.getFloatTimeDomainData(samples);
      let sum = 0;
      for (const sample of samples) {
        sum += sample * sample;
      }
      const rms = Math.sqrt(sum / samples.length);
      // The bar is written straight to the DOM: at 60fps this would re-render
      // the whole card, and only the speaking/quiet flip is React's business.
      if (meterRef.current) {
        const scale = Math.min(1, rms / 0.25);
        meterRef.current.style.transform = `scaleX(${scale.toFixed(3)})`;
      }
      const now = performance.now();
      if (rms >= VOICE_ON) {
        voiceSinceRef.current = now;
        setMicSpeaking(true);
      } else if (voiceSinceRef.current && now - voiceSinceRef.current > VOICE_OFF_MS) {
        voiceSinceRef.current = 0;
        setMicSpeaking(false);
        // The patient just finished a turn, so a reply is now owed. Cleared by
        // EIR's first transcription delta.
        setAwaitingReply(true);
      }
    };
    meterFrameRef.current = requestAnimationFrame(tick);
  }

  function routeStreamToSpeakers(stream: MediaStream | null | undefined) {
    if (!stream || routedStreams.current.has(stream)) {
      return;
    }
    routedStreams.current.add(stream);
    const ctx = ctxRef.current;
    if (!ctx) {
      return;
    }
    void ctx.resume().then(() => {
      try {
        const source = ctx.createMediaStreamSource(stream);
        source.connect(ctx.destination);
        voiceDebug.info("remote stream routed via Web Audio");
      } catch (err) {
        voiceDebug.warn("Web Audio route failed", err);
      }
    });
  }

  function mountRemoteElement(element: HTMLMediaElement) {
    if (element instanceof HTMLVideoElement) {
      return;
    }
    const container = document.getElementById("eir-remote-media");
    if (container && element.parentElement !== container) {
      container.replaceChildren(element);
    }
    element.muted = false;
    element.volume = 1;
    element.autoplay = true;
    element.controls = false;
    element.setAttribute("playsinline", "true");
    if (element.srcObject instanceof MediaStream) {
      routeStreamToSpeakers(element.srcObject);
    }
    element.addEventListener(
      "loadedmetadata",
      () => {
        if (element.srcObject instanceof MediaStream) {
          routeStreamToSpeakers(element.srcObject);
        }
      },
      { once: true },
    );
    void element.play().then(
      () => {
        voiceDebug.info("remote element playing");
        setAudioState("playing");
      },
      () => setAudioState("blocked"),
    );
  }

  function hookRenderer(renderer: PreviewRenderer) {
    if (renderer.kind === "video") {
      voiceDebug.info("ignoring video renderer");
      return;
    }
    renderer.enable();
    const container = document.getElementById("eir-remote-media");
    renderer.render(container ?? undefined);
    if (renderer.element) {
      mountRemoteElement(renderer.element);
    } else if (renderer.stream) {
      routeStreamToSpeakers(renderer.stream);
    }
    voiceDebug.info("remote renderer attached", renderer.kind ?? "unknown");
  }

  function wireEndpoint(endpoint: PreviewEndpoint) {
    if (wiredEndpoints.current.has(endpoint)) {
      return;
    }
    wiredEndpoints.current.add(endpoint);
    const events = eventsRef.current;
    if (!events?.EndpointEvents?.RemoteMediaAdded) {
      return;
    }
    for (const renderer of endpoint.mediaRenderers ?? []) {
      hookRenderer(renderer);
    }
    endpoint.on(events.EndpointEvents.RemoteMediaAdded, (payload) => {
      const renderer = (payload as { mediaRenderer?: PreviewRenderer }).mediaRenderer;
      if (renderer) {
        hookRenderer(renderer);
      }
    });
  }

  function attachRemote(call: PreviewCall) {
    for (const endpoint of call.getEndpoints()) {
      wireEndpoint(endpoint);
    }
  }

  function getRawPeerConnection(call: PreviewCall): RTCPeerConnection | null {
    return call.peerConnection?.peerConnection ?? null;
  }

  function logPeerState(call: PreviewCall, label: string) {
    const pc = getRawPeerConnection(call);
    if (!pc) {
      voiceDebug.info(`${label}: no peerConnection yet`);
      return;
    }
    voiceDebug.info(`${label}: ice=${pc.iceConnectionState} conn=${pc.connectionState}`);
  }

  function readStats(payload: unknown) {
    const stats = (payload as {
      stats?: { inbound?: { audio?: { bytesReceived?: number } }; outbound?: { audio?: { bytesSent?: number } } };
    }).stats;
    const remote = stats?.inbound?.audio?.bytesReceived ?? 0;
    const mic = stats?.outbound?.audio?.bytesSent ?? 0;
    if (remote > remoteBytesRef.current) {
      remoteBytesRef.current = remote;
      setAudioState("playing");
    }
    if (mic > micBytesRef.current) {
      micBytesRef.current = mic;
      setMicSending(true);
    }
  }

  function wireCall(call: PreviewCall) {
    const events = eventsRef.current;
    if (!events) {
      return;
    }
    call.on(events.CallEvents.MessageReceived, (payload) => {
      const raw = String((payload as { text?: string }).text || "");
      try {
        const parsed = JSON.parse(raw) as { r?: string; d?: string; i?: number; eid?: string; f?: number };
        if (parsed.eid) {
          setEpisodeId(parsed.eid);
        }
        // The scenario sends one delta per Gemini transcription chunk, tagged
        // with the turn it belongs to. Chunks are appended, never reconciled.
        const role: TranscriptRole | null =
          parsed.r === "p" ? "you" : parsed.r === "a" ? "eir" : null;
        if (role && typeof parsed.i === "number") {
          const turn = parsed.i;
          const delta = typeof parsed.d === "string" ? parsed.d : "";
          const finished = parsed.f === 1;
          if (role === "eir" && delta) {
            setAwaitingReply(false);
          }
          setLines((current) => appendTranscript(current, turn, role, delta, finished));
        }
      } catch {
        // ignore non-JSON signaling
      }
    });
    call.on(events.CallEvents.EndpointAdded, (payload) => {
      const endpoint = (payload as { endpoint?: PreviewEndpoint }).endpoint;
      if (endpoint) {
        voiceDebug.info("endpoint added");
        wireEndpoint(endpoint);
      }
    });
    call.on(events.CallEvents.Connected, () => {
      voiceDebug.info("call connected");
      call.unmutePlayback();
      attachRemote(call);
      logPeerState(call, "connected");
      startMicMeter(call);
      setAudioState("waiting");
      setStatus("in_call");
    });
    call.on(events.CallEvents.ICECompleted, () => {
      voiceDebug.info("ICE completed");
      logPeerState(callRef.current ?? call, "ice-completed");
    });
    call.on(events.CallEvents.ICETimeout, () => {
      voiceDebug.warn("ICE timeout");
    });
    call.on(events.CallEvents.MediaElementCreated, (payload) => {
      const element = (payload as { element?: HTMLMediaElement }).element;
      if (element) {
        voiceDebug.info("media element created");
        mountRemoteElement(element);
      }
    });
    call.on(events.CallEvents.CallStatsReceived, (payload) => {
      readStats(payload);
    });
    call.on(events.CallEvents.Disconnected, () => {
      voiceDebug.info("call disconnected");
      callRef.current = null;
      stopMicMeter();
      setStatus("ended");
      setAudioState("idle");
      setMicSending(false);
      setAwaitingReply(false);
    });
    call.on(events.CallEvents.Failed, (payload) => {
      const failed = payload as { code?: number; reason?: string };
      voiceDebug.error("call failed", failed.code, failed.reason);
      callRef.current = null;
      stopMicMeter();
      setStatus("ended");
      setAudioState("idle");
      setMicSending(false);
      setAwaitingReply(false);
    });
  }

  /** Log in with a server-signed one-time key. The password never reaches this browser. */
  async function authenticate(
    sdk: ReturnType<typeof VoxSdk.getInstance>,
    targetEpisode: string,
  ) {
    const login = config?.login;
    if (!login) {
      throw new Error("Browser voice is not configured on this deployment");
    }
    const requested = (await sdk.requestOneTimeLoginKey(login)) as {
      key?: string;
      code?: number;
    };
    if (!requested?.key) {
      throw new Error(
        `Voximplant did not issue a one-time key${requested?.code ? ` (${requested.code})` : ""}`,
      );
    }
    const session = await startVoiceWebSession(targetEpisode, requested.key);
    const auth = (await sdk.loginWithOneTimeKey(session.login, session.hash)) as {
      result?: boolean;
      code?: number;
    };
    if (auth && auth.result === false) {
      throw new Error(`Voximplant login failed${auth.code ? ` (${auth.code})` : ""}`);
    }
    return session;
  }

  async function startCheckin() {
    const targetEpisode = episodeId;
    if (!signedInAsPatient) {
      setError("Sign in as a patient before starting a check-in.");
      return;
    }
    if (!targetEpisode) {
      setError("No active recovery episode to check in on.");
      return;
    }
    setBusy(true);
    setError(null);
    setLines([]);
    setStatus("connecting");
    try {
      // Unlock audio inside the click, before any await, or Safari keeps it suspended.
      await resumeAudioContext();

      const VoxImplant = await loadVoxSdk();
      eventsRef.current = VoxImplant;
      const sdk = VoxImplant.getInstance();
      sdkRef.current = sdk;

      if (!micHandlerSet.current) {
        micHandlerSet.current = true;
        sdk.on(VoxImplant.Events.MicAccessResult, (payload) => {
          const granted = (payload as { result?: boolean }).result !== false;
          setMicReady(granted);
          voiceDebug.info("mic access", granted ? "granted" : "denied");
        });
      }

      try {
        await sdk.init({
          node: VoxImplant.ConnectionNode.NODE_2,
          micRequired: true,
          progressTone: false,
          showDebugInfo: true,
          rtcStatsCollectionInterval: 3,
        });
        setMicReady(true);
      } catch (initError) {
        if (!/already/i.test(describeError(initError))) {
          throw initError;
        }
      }

      // The SDK is a singleton, and a successful login leaves it in LOGGED_IN
      // rather than CONNECTED. Treating only CONNECTED as "up" would reconnect
      // and re-run the one-time key handshake on every later check-in, so the
      // client state decides: LOGGED_IN just needs fresh custom data.
      let state = sdk.getClientState();
      if (
        state !== VoxImplant.ClientState.CONNECTED &&
        state !== VoxImplant.ClientState.LOGGED_IN
      ) {
        await sdk.connect();
        state = sdk.getClientState();
      }
      const session =
        state === VoxImplant.ClientState.LOGGED_IN
          ? await startVoiceWebSession(targetEpisode)
          : await authenticate(sdk, targetEpisode);

      setStatus("dialing");
      remoteBytesRef.current = 0;
      micBytesRef.current = 0;
      wiredEndpoints.current = new WeakSet();
      stopMicMeter();
      setMicSending(false);
      setAwaitingReply(false);

      const call = sdk.call({
        number: session.number,
        video: { sendVideo: false, receiveVideo: false },
        customData: session.custom_data,
      }) as unknown as PreviewCall;
      callRef.current = call;
      wireCall(call);
      // Status advances to in_call from the Connected handler, so the timer
      // measures the conversation rather than the dial.
    } catch (err) {
      setStatus("idle");
      setError(describeError(err));
    } finally {
      setBusy(false);
    }
  }

  async function tapToPlay() {
    try {
      await resumeAudioContext();
      document.querySelectorAll("#eir-remote-media audio, #eir-remote-media video").forEach((node) => {
        if (node instanceof HTMLMediaElement) {
          mountRemoteElement(node);
        }
      });
      callRef.current?.unmutePlayback();
      if (callRef.current) {
        attachRemote(callRef.current);
      }
    } catch (err) {
      setError(describeError(err));
    }
  }

  function hangup() {
    try {
      callRef.current?.hangup();
    } catch {
      // ignore
    }
    callRef.current = null;
    stopMicMeter();
    setStatus("ended");
    setAudioState("idle");
    setAwaitingReply(false);
  }

  const dialing = status === "dialing";
  const live = status === "in_call";
  const lastLine = lines[lines.length - 1];
  const phase: Phase = !live
    ? "idle"
    : micSpeaking
      ? "hearing"
      : lastLine?.role === "eir" && lastLine.pending
        ? "speaking"
        : awaitingReply || lastLine?.role === "you"
          ? "thinking"
          : "listening";
  const idle = status === "idle" || status === "ended";
  const disabled = busy || !episodeId || !signedInAsPatient || config?.enabled === false;

  return (
    <div className="flex flex-col gap-6">
      <p className="max-w-[74ch] text-[14px] leading-[1.6] text-secondary">
        Audio runs over WebRTC — no phone call is placed and no number is dialled. Allow the
        microphone when your browser asks.
      </p>

      {error ? <ErrorAlert message={error} /> : null}

      <div className="grid items-start gap-7 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <section className="flex flex-col">
          {/* the call itself — accent is agent activity, ink is at rest */}
          <div
            className={`on-ink flex flex-col items-center px-6 py-9 text-center ${
              dialing || live ? "bg-accent" : "bg-ink"
            }`}
          >
            <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-on-ink-muted">
              EIR Recovery
            </span>
            <p className="mt-4 text-[22px] font-medium text-paper">{statusLabel(status)}</p>
            <p className="mt-3 font-mono text-[38px] leading-none tabular-nums text-paper">
              {live ? formatTimer(elapsed) : "00:00"}
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <span className="inline-flex items-center gap-2 border border-on-ink-rule px-2.5 py-1 font-mono text-[11px] text-on-ink">
                {dialing ? (
                  <span className="eir-pulse h-1.5 w-1.5 bg-paper" aria-hidden />
                ) : null}
                {micReady ? (micSending ? "Mic sending" : "Mic ready") : "Mic pending"}
              </span>
              <span className="inline-flex items-center border border-on-ink-rule px-2.5 py-1 font-mono text-[11px] text-on-ink">
                {audioLabel(audioState)}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-4 border-b border-rule pt-5">
            {idle || status === "connecting" ? (
              <div className="flex flex-col gap-4">
                <p className="text-[14px] leading-[1.6] text-secondary">
                  EIR will ask about your pain level, symptoms, and medication, then flag anything
                  that needs a clinician. It does not diagnose.
                </p>
                {loadingEpisode ? (
                  <p className="font-mono text-[11.5px] text-muted">
                    Finding your recovery episode…
                  </p>
                ) : !signedInAsPatient ? (
                  <p className="border-l-[3px] border-warn bg-warn-tint px-4 py-3 text-[12.5px] leading-[1.6] text-warn">
                    Sign in as a patient to start a check-in. Your session is missing or has
                    expired — demo sessions last 24 hours, and this developer page has no sign-in
                    step of its own.{" "}
                    <a className="font-medium underline" href="/login">
                      Go to sign-in
                    </a>{" "}
                    (demo patient <span className="font-mono">alex</span> /{" "}
                    <span className="font-mono">demo-alex</span>), then come back here.
                  </p>
                ) : episodeId ? (
                  <p className="font-mono text-[11.5px] text-muted">
                    episode {episodeId.slice(0, 8)} ·{" "}
                    {config?.gemini_live_voice ?? "Gemini Live"} · {VOX_PREVIEW_NODE}
                  </p>
                ) : (
                  <p className="border-l-[3px] border-warn bg-warn-tint px-4 py-3 text-[12.5px] leading-[1.6] text-warn">
                    No active recovery episode found for your account.
                  </p>
                )}
                {config?.enabled === false ? (
                  <p className="border-l-[3px] border-warn bg-warn-tint px-4 py-3 text-[12.5px] leading-[1.6] text-warn">
                    Browser voice is not configured on this deployment, so the check-in cannot
                    start. The rest of the recovery workspace is unaffected.
                  </p>
                ) : null}
                <Button onClick={() => void startCheckin()} disabled={disabled} className="w-full">
                  {busy
                    ? "Connecting…"
                    : status === "ended"
                      ? "Start another check-in"
                      : "Start voice check-in"}
                </Button>
              </div>
            ) : null}

            {dialing ? (
              <p className="border-l-[3px] border-accent bg-raised px-4 py-3 text-[13.5px] text-secondary">
                Connecting you to the recovery assistant…
              </p>
            ) : null}

            <div className="flex flex-wrap gap-2">
              {live ? (
                <Button variant="destructive" onClick={hangup} className="flex-1">
                  End check-in
                </Button>
              ) : null}
              {(live || dialing) && audioState === "blocked" ? (
                <Button variant="secondary" onClick={() => void tapToPlay()} className="flex-1">
                  Unlock sound
                </Button>
              ) : null}
            </div>

            {live ? (
              <div
                className={`flex flex-col gap-3 border-l-[3px] px-4 py-3.5 ${
                  phase === "hearing"
                    ? "border-accent bg-raised"
                    : phase === "thinking"
                      ? "border-warn bg-warn-tint"
                      : "border-rule-strong bg-raised"
                }`}
                aria-live="polite"
              >
                <div className="flex items-center gap-2.5">
                  <span
                    aria-hidden
                    className={`h-1.5 w-1.5 shrink-0 ${
                      phase === "hearing"
                        ? "bg-accent"
                        : phase === "thinking"
                          ? "eir-pulse bg-warn"
                          : phase === "speaking"
                            ? "bg-ink"
                            : "bg-inactive"
                    }`}
                  />
                  <span
                    className={`font-mono text-[12px] ${
                      phase === "thinking" ? "text-warn" : "text-ink"
                    }`}
                  >
                    {phaseLabel(phase)}
                  </span>
                </div>
                {/* Driven by requestAnimationFrame through meterRef, not React state. */}
                <div className="h-1.5 overflow-hidden bg-hover">
                  <div
                    ref={meterRef}
                    className="h-full origin-left bg-accent transition-transform duration-75"
                    style={{ transform: "scaleX(0)" }}
                  />
                </div>
                <p className="font-mono text-[11px] text-muted">{audioLabel(audioState)}</p>
              </div>
            ) : (
              <p className="border border-dashed border-rule-strong px-3 py-4 text-center font-mono text-[11.5px] text-muted">
                Audio starts playing here once the check-in begins.
              </p>
            )}
            {/* The SDK appends its <audio> element here, not into the box above:
                React owns that node's children and would fight the SDK over it.
                Hidden because the panel already reports transport state. */}
            <div id="eir-remote-media" className="hidden" aria-hidden="true" />
          </div>
        </section>

        <section className="flex min-w-0 flex-col">
          <SectionHeader
            title="Live transcript"
            description="Turns build up as Gemini hears and speaks. The transcript stays in this browser session only and is never saved to the episode."
            actionHref={episodeId ? `/recovery/${episodeId}` : undefined}
            actionLabel={episodeId ? "Open episode" : undefined}
          />
          <div
            ref={transcriptRef}
            className="flex max-h-[34rem] min-h-[28rem] flex-col gap-4 overflow-y-auto"
          >
            {lines.length === 0 ? (
              <p className="font-mono text-[12px] text-muted">
                {idle ? "Transcript appears here once the check-in starts." : phaseLabel(phase)}
              </p>
            ) : (
              lines.map((line) => (
                <div
                  key={line.id}
                  className={
                    line.role === "eir"
                      ? "max-w-[92%] border-l-[3px] border-accent px-4 py-3"
                      : "ml-auto max-w-[92%] bg-raised px-4 py-3"
                  }
                >
                  <div className="mb-1.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                    <span>{line.role === "eir" ? "EIR" : "You"}</span>
                    {line.pending ? <span className="normal-case">typing…</span> : null}
                  </div>
                  <p className="text-[14px] leading-[1.6] text-body">{line.text}</p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
