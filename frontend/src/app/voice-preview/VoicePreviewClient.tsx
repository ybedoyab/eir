"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type * as VoxSdk from "voximplant-websdk";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  previewSipLogin,
  VOX_PREVIEW_ACCOUNT,
  VOX_PREVIEW_APP,
  VOX_PREVIEW_NODE,
  VOX_PREVIEW_USER,
} from "@/lib/voximplantPreview";
import { createLocalRinger } from "@/lib/voiceRingtone";
import { applyTranscript, type TranscriptLine } from "@/lib/voiceTranscript";

type Status = "idle" | "connecting" | "ready" | "incoming" | "in_call" | "ended";
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
  answer: (
    customData?: string,
    extraHeaders?: Record<string, string>,
    useVideo?: { sendVideo?: boolean; receiveVideo?: boolean },
  ) => void;
  hangup: () => void;
  unmutePlayback: () => void;
  getEndpoints: () => PreviewEndpoint[];
  on: (event: unknown, handler: (payload: unknown) => void) => void;
  peerConnection?: { peerConnection?: RTCPeerConnection };
};

function describeError(err: unknown): string {
  if (err instanceof Error && err.message) {
    return err.message;
  }
  if (typeof err === "string" && err.trim()) {
    return err;
  }
  if (err && typeof err === "object") {
    const rec = err as { message?: unknown; code?: unknown };
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
  if (status === "incoming") {
    return "Incoming call";
  }
  if (status === "in_call") {
    return "Connected";
  }
  if (status === "ready") {
    return "Waiting for call";
  }
  if (status === "connecting") {
    return "Connecting…";
  }
  if (status === "ended") {
    return "Call ended";
  }
  return "Preview line";
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
  const ringerRef = useRef<ReturnType<typeof createLocalRinger> | null>(null);
  const eventsRef = useRef<typeof VoxSdk | null>(null);
  const callRef = useRef<PreviewCall | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const remoteBytesRef = useRef(0);
  const micBytesRef = useRef(0);
  const routedStreams = useRef(new WeakSet<MediaStream>());
  const wiredEndpoints = useRef(new WeakSet<object>());
  const incomingHandlerSet = useRef(false);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [micReady, setMicReady] = useState(false);
  const [micSending, setMicSending] = useState(false);
  const [audioState, setAudioState] = useState<AudioState>("idle");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [episodeId, setEpisodeId] = useState<string | null>(null);
  const [lines, setLines] = useState<TranscriptLine[]>([]);

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

  useEffect(() => {
    return () => {
      ringerRef.current?.stop();
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
        console.info("[eir-voice] remote stream routed via Web Audio");
      } catch (err) {
        console.warn("[eir-voice] Web Audio route failed", err);
      }
    });
  }

  function stopRingtone() {
    ringerRef.current?.stop();
    ringerRef.current = null;
  }

  async function startRingtone() {
    const ctx = await resumeAudioContext();
    stopRingtone();
    ringerRef.current = createLocalRinger(ctx);
    ringerRef.current.start();
  }

  function mountRemoteElement(element: HTMLMediaElement) {
    const container = document.getElementById("eir-remote-media");
    if (container && element.parentElement !== container) {
      container.replaceChildren(element);
    }
    element.muted = false;
    element.volume = 1;
    element.autoplay = true;
    element.controls = true;
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
        console.info("[eir-voice] remote element playing");
        setAudioState("playing");
      },
      () => setAudioState("blocked"),
    );
  }

  function hookRenderer(renderer: PreviewRenderer) {
    renderer.enable();
    const container = document.getElementById("eir-remote-media");
    renderer.render(container ?? undefined);
    if (renderer.element) {
      mountRemoteElement(renderer.element);
    } else if (renderer.stream) {
      routeStreamToSpeakers(renderer.stream);
    }
    console.info("[eir-voice] remote renderer attached", renderer.kind ?? "unknown");
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
      console.info(`[eir-voice] ${label}: no peerConnection yet`);
      return;
    }
    console.info(`[eir-voice] ${label}: ice=${pc.iceConnectionState} conn=${pc.connectionState}`);
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
        console.info("[eir-voice] endpoint added");
        wireEndpoint(endpoint);
      }
    });
    call.on(events.CallEvents.Connected, () => {
      console.info("[eir-voice] call connected");
      call.unmutePlayback();
      attachRemote(call);
      logPeerState(call, "connected");
      setAudioState("waiting");
    });
    call.on(events.CallEvents.ICECompleted, () => {
      console.info("[eir-voice] ICE completed");
      logPeerState(callRef.current ?? call, "ice-completed");
    });
    call.on(events.CallEvents.ICETimeout, () => {
      console.warn("[eir-voice] ICE timeout");
    });
    call.on(events.CallEvents.MediaElementCreated, (payload) => {
      const element = (payload as { element?: HTMLMediaElement }).element;
      if (element) {
        console.info("[eir-voice] media element created");
        mountRemoteElement(element);
      }
    });
    call.on(events.CallEvents.CallStatsReceived, (payload) => {
      readStats(payload);
    });
    call.on(events.CallEvents.Disconnected, () => {
      console.info("[eir-voice] call disconnected");
      stopRingtone();
      callRef.current = null;
      setStatus("ended");
      setAudioState("idle");
      setMicSending(false);
    });
    call.on(events.CallEvents.Failed, (payload) => {
      const failed = payload as { code?: number; reason?: string };
      console.error("[eir-voice] call failed", failed.code, failed.reason);
      stopRingtone();
      callRef.current = null;
      setStatus("ended");
      setAudioState("idle");
      setMicSending(false);
    });
  }

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const password = String(new FormData(event.currentTarget).get("password") || "");
    if (!password) {
      setError("Password is required. Use .voximplant-preview.env.");
      return;
    }
    setBusy(true);
    setError(null);
    setLines([]);
    setStatus("connecting");
    try {
      const VoxImplant = await loadVoxSdk();
      eventsRef.current = VoxImplant;
      const sdk = VoxImplant.getInstance();
      sdkRef.current = sdk;

      if (!incomingHandlerSet.current) {
        incomingHandlerSet.current = true;
        sdk.on(VoxImplant.Events.IncomingCall, (incoming) => {
          const call = incoming.call as unknown as PreviewCall;
          callRef.current = call;
          remoteBytesRef.current = 0;
          micBytesRef.current = 0;
          wiredEndpoints.current = new WeakSet();
          setMicSending(false);
          wireCall(call);
          void startRingtone();
          setStatus("incoming");
        });
        sdk.on(VoxImplant.Events.MicAccessResult, (payload) => {
          const granted = (payload as { result?: boolean }).result !== false;
          setMicReady(granted);
          console.info("[eir-voice] mic access", granted ? "granted" : "denied");
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
      await sdk.connect();
      const auth = (await sdk.login(previewSipLogin(), password)) as { result?: boolean; code?: number };
      if (auth && auth.result === false) {
        throw new Error(`Voximplant login failed${auth.code ? ` (${auth.code})` : ""}`);
      }
      setStatus("ready");
    } catch (err) {
      setStatus("idle");
      setError(describeError(err));
    } finally {
      setBusy(false);
    }
  }

  async function answer() {
    const call = callRef.current;
    if (!call) {
      return;
    }
    stopRingtone();
    try {
      await resumeAudioContext();
    } catch (err) {
      setError(describeError(err));
      return;
    }
    console.info("[eir-voice] answering call");
    call.answer("", {}, { sendVideo: false, receiveVideo: false });
    call.unmutePlayback();
    window.setTimeout(() => logPeerState(call, "post-answer"), 1500);
    window.setTimeout(() => logPeerState(call, "post-answer+4s"), 4000);
    setAudioState("waiting");
    setStatus("in_call");
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
    stopRingtone();
    try {
      callRef.current?.hangup();
    } catch {
      // ignore
    }
    callRef.current = null;
    setStatus("ready");
    setAudioState("idle");
  }

  const waiting = status === "ready";
  const ringing = status === "incoming";
  const live = status === "in_call";

  return (
    <div>
      <PageHeader
        eyebrow="Voice preview"
        title="Live recovery call"
        description="Close phone.voximplant.com first. Connect here, wait for the line to open, then answer when EIR rings. Hard-refresh (Ctrl+Shift+R) if a previous call failed."
      />
      {error ? <ErrorAlert message={error} /> : null}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <Card className="overflow-hidden p-0">
          <div
            className={`relative px-6 py-10 text-center text-white ${
              ringing ? "bg-emerald-700" : live ? "bg-teal-800" : "bg-slate-800"
            }`}
          >
            {ringing ? (
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
            {status === "idle" || status === "connecting" || status === "ended" ? (
              <form className="space-y-4" onSubmit={connect}>
                <label className="block text-sm text-slate-700">
                  Username
                  <input
                    readOnly
                    autoComplete="username"
                    value={VOX_PREVIEW_USER}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                  />
                </label>
                <label className="block text-sm text-slate-700">
                  Password
                  <input
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  />
                </label>
                <p className="text-xs text-slate-500">
                  {VOX_PREVIEW_APP} · {VOX_PREVIEW_ACCOUNT} · {VOX_PREVIEW_NODE}
                </p>
                <Button type="submit" disabled={busy} className="w-full">
                  {busy ? "Connecting…" : "Connect line and wait"}
                </Button>
              </form>
            ) : null}

            {ringing ? (
              <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                EIR is calling. Answer here to hear the recovery agent.
              </p>
            ) : null}

            {waiting ? (
              <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Line is open. Ask the agent to place the preview call.
              </p>
            ) : null}

            <div className="flex flex-wrap gap-2">
              {ringing ? (
                <Button onClick={() => void answer()} className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                  Answer call
                </Button>
              ) : null}
              {live ? (
                <Button variant="danger" onClick={hangup} className="flex-1">
                  End call
                </Button>
              ) : null}
              {(live || ringing) && audioState === "blocked" ? (
                <Button variant="secondary" onClick={() => void tapToPlay()} className="flex-1">
                  Unlock sound
                </Button>
              ) : null}
            </div>

            <div id="eir-remote-media" className="min-h-12 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-xs text-slate-500">
              {live ? null : "Remote audio player appears here after you answer."}
            </div>
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
                {waiting
                  ? "Transcript appears here once the call starts."
                  : ringing
                    ? "Answer the call to start the transcript."
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
