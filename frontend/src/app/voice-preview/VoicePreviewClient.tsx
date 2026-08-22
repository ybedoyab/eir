"use client";

import { useEffect, useRef, useState } from "react";
import type * as VoxSdk from "voximplant-websdk";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { clearSession, loadSession } from "@/lib/auth";
import { VOX_PREVIEW_NODE } from "@/lib/voximplantPreview";
import { applyTranscript, type TranscriptLine } from "@/lib/voiceTranscript";
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
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [micReady, setMicReady] = useState(false);
  const [micSending, setMicSending] = useState(false);
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
        const parsed = JSON.parse(raw) as { r?: string; t?: string; eid?: string; f?: number };
        if (parsed.eid) {
          setEpisodeId(parsed.eid);
        }
        const finished = parsed.f === 1;
        if (parsed.r === "p" && parsed.t) {
          setLines((current) => applyTranscript(current, "you", parsed.t!, finished));
        }
        if (parsed.r === "a" && parsed.t) {
          setLines((current) => applyTranscript(current, "eir", parsed.t!, finished));
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
      setStatus("ended");
      setAudioState("idle");
      setMicSending(false);
    });
    call.on(events.CallEvents.Failed, (payload) => {
      const failed = payload as { code?: number; reason?: string };
      voiceDebug.error("call failed", failed.code, failed.reason);
      callRef.current = null;
      setStatus("ended");
      setAudioState("idle");
      setMicSending(false);
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
      setMicSending(false);

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
    setStatus("ended");
    setAudioState("idle");
  }

  const dialing = status === "dialing";
  const live = status === "in_call";
  const idle = status === "idle" || status === "ended";
  const disabled = busy || !episodeId || !signedInAsPatient || config?.enabled === false;

  return (
    <div>
      <PageHeader
        eyebrow="Voice check-in"
        title="Talk to EIR"
        description="Start a spoken recovery check-in in this tab. Audio runs over WebRTC — no phone call is placed and no number is dialled. Allow the microphone when your browser asks."
      />
      {error ? <ErrorAlert message={error} /> : null}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <Card className="overflow-hidden p-0">
          <div
            className={`relative px-6 py-10 text-center text-white ${
              dialing ? "bg-emerald-700" : live ? "bg-teal-800" : "bg-slate-800"
            }`}
          >
            {dialing ? (
              <span className="absolute inset-x-0 top-4 mx-auto h-16 w-16 animate-ping rounded-full bg-white/20" />
            ) : null}
            <p className="relative text-xs uppercase tracking-[0.24em] text-white/70">EIR Recovery</p>
            <p className="relative mt-4 text-2xl font-semibold">{statusLabel(status)}</p>
            <p className="relative mt-3 font-mono text-4xl tabular-nums">{live ? formatTimer(elapsed) : "00:00"}</p>
            <div className="relative mt-5 flex flex-wrap justify-center gap-2 text-xs">
              <span className="rounded-full bg-white/15 px-3 py-1">
                {micReady ? (micSending ? "Mic sending" : "Mic ready") : "Mic pending"}
              </span>
              <span className="rounded-full bg-white/15 px-3 py-1">{audioLabel(audioState)}</span>
            </div>
          </div>
          <div className="space-y-4 p-6">
            {idle || status === "connecting" ? (
              <div className="space-y-4">
                <p className="text-sm text-slate-700">
                  EIR will ask about your pain level, symptoms, and medication, then flag
                  anything that needs a clinician. It does not diagnose.
                </p>
                {loadingEpisode ? (
                  <p className="text-xs text-slate-500">Finding your recovery episode…</p>
                ) : !signedInAsPatient ? (
                  <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
                    Sign in as a patient to start a check-in. Your session is missing or has
                    expired — demo sessions last 24 hours, and this developer page has no
                    sign-in step of its own.{" "}
                    <a className="font-medium underline" href="/login">
                      Go to sign-in
                    </a>{" "}
                    (demo patient <span className="font-mono">alex</span> /{" "}
                    <span className="font-mono">demo-alex</span>), then come back here.
                  </p>
                ) : episodeId ? (
                  <p className="text-xs text-slate-500">
                    Episode <span className="font-mono">{episodeId.slice(0, 8)}</span> ·{" "}
                    {config?.gemini_live_voice ?? "Gemini Live"} · {VOX_PREVIEW_NODE}
                  </p>
                ) : (
                  <p className="text-xs text-amber-700">
                    No active recovery episode found for your account.
                  </p>
                )}
                {config?.enabled === false ? (
                  <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
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
              <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                Connecting you to the recovery assistant…
              </p>
            ) : null}

            <div className="flex flex-wrap gap-2">
              {live ? (
                <Button variant="danger" onClick={hangup} className="flex-1">
                  End check-in
                </Button>
              ) : null}
              {(live || dialing) && audioState === "blocked" ? (
                <Button variant="secondary" onClick={() => void tapToPlay()} className="flex-1">
                  Unlock sound
                </Button>
              ) : null}
            </div>

            <div className="min-h-12 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-xs text-slate-500">
              {live ? audioLabel(audioState) : "Audio starts playing here once the check-in begins."}
            </div>
            {/* The SDK appends its <audio> element here, not into the box above:
                React owns that node's children and would fight the SDK over it.
                Hidden because the card already reports transport state. */}
            <div id="eir-remote-media" className="hidden" aria-hidden="true" />
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Live transcript"
            description="Turns build up as Gemini hears and speaks. Transcript stays in this browser session only and is not saved to the episode."
            action={
              episodeId ? (
                <a className="text-sm font-medium text-teal-700 hover:text-teal-800" href={`/recovery/${episodeId}`}>
                  Open episode
                </a>
              ) : null
            }
          />
          <div
            ref={transcriptRef}
            className="flex max-h-[34rem] min-h-[28rem] flex-col gap-3 overflow-y-auto rounded-xl bg-slate-50 p-4"
          >
            {lines.length === 0 ? (
              <p className="text-sm text-slate-500">
                {idle
                  ? "Transcript appears here once the check-in starts."
                  : "Waiting for the first spoken turn…"}
              </p>
            ) : (
              lines.map((line, index) => (
                <div
                  key={`${line.role}-${index}-${line.text.slice(0, 24)}`}
                  className={
                    line.role === "eir"
                      ? "max-w-[92%] rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 shadow-sm"
                      : "ml-auto max-w-[92%] rounded-2xl bg-teal-700 px-4 py-3 text-sm text-white"
                  }
                >
                  <div className="mb-1 flex items-center gap-2 text-[11px] uppercase tracking-wide opacity-70">
                    <span>{line.role === "eir" ? "EIR" : "You"}</span>
                    {line.pending ? <span className="normal-case">typing…</span> : null}
                  </div>
                  {line.text}
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
