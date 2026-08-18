"use client";

import { useRef, useState } from "react";
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

type Status = "idle" | "connecting" | "ready" | "incoming" | "in_call" | "ended";
type PreviewCall = {
  answer: (
    customData?: string,
    extraHeaders?: Record<string, string>,
    useVideo?: { sendVideo?: boolean; receiveVideo?: boolean },
  ) => void;
  hangup: () => void;
  unmutePlayback: () => void;
  unmuteMicrophone: () => void;
  getEndpoints: () => Array<{
    mediaRenderers: Array<{
      enable: () => void;
      render: (container?: HTMLElement) => void;
      element?: HTMLMediaElement;
    }>;
  }>;
  on: (event: unknown, handler: (payload: unknown) => void) => void;
};

function forcePlay(container: HTMLElement, onPlaying: () => void) {
  for (const media of container.querySelectorAll("audio, video")) {
    const element = media as HTMLMediaElement;
    element.autoplay = true;
    element.setAttribute("playsinline", "true");
    element.muted = false;
    element.volume = 1;
    void element.play().then(onPlaying).catch(() => undefined);
  }
}

export default function VoicePreviewClient() {
  const mediaRef = useRef<HTMLDivElement | null>(null);
  const sdkRef = useRef<ReturnType<typeof VoxSdk.getInstance> | null>(null);
  const eventsRef = useRef<typeof VoxSdk | null>(null);
  const callRef = useRef<PreviewCall | null>(null);
  const playTimer = useRef<number | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false);

  function markPlaying() {
    setPlaying(true);
  }

  function startPlaybackWatch(call: PreviewCall) {
    const container = mediaRef.current;
    if (!container) {
      return;
    }
    const events = eventsRef.current;
    const pump = () => {
      try {
        call.unmutePlayback();
        call.unmuteMicrophone();
      } catch {
        // ignore
      }
      for (const endpoint of call.getEndpoints()) {
        for (const renderer of endpoint.mediaRenderers || []) {
          renderer.enable();
          renderer.render(container);
          if (renderer.element) {
            renderer.element.muted = false;
            renderer.element.autoplay = true;
            void renderer.element.play().then(markPlaying).catch(() => undefined);
          }
        }
      }
      forcePlay(container, markPlaying);
    };
    if (events) {
      call.on(events.CallEvents.Connected, pump);
    }
    pump();
    if (playTimer.current) {
      window.clearInterval(playTimer.current);
    }
    playTimer.current = window.setInterval(pump, 500);
    window.setTimeout(() => {
      if (playTimer.current) {
        window.clearInterval(playTimer.current);
        playTimer.current = null;
      }
    }, 8000);
  }

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    if (!password) {
      setError("Password is required. Use VOXIMPLANT_PREVIEW_PASSWORD from .voximplant-preview.env.");
      return;
    }
    setBusy(true);
    setError(null);
    setPlaying(false);
    setStatus("connecting");
    try {
      const VoxImplant = await import("voximplant-websdk");
      eventsRef.current = VoxImplant;
      const sdk = VoxImplant.getInstance();
      sdkRef.current = sdk;
      sdk.on(VoxImplant.Events.IncomingCall, (incoming) => {
        const call = incoming.call as unknown as PreviewCall;
        callRef.current = call;
        setStatus("incoming");
        call.on(VoxImplant.CallEvents.Disconnected, () => {
          callRef.current = null;
          setStatus("ended");
        });
        call.on(VoxImplant.CallEvents.Failed, () => {
          callRef.current = null;
          setStatus("ended");
        });
      });
      await sdk.init({
        node: VoxImplant.ConnectionNode.NODE_2,
        micRequired: true,
        progressTone: true,
        progressToneCountry: "US",
        remoteVideoContainerId: "eir-remote-media",
        showWarnings: true,
      });
      await sdk.connect();
      const auth = (await sdk.login(previewSipLogin(), password)) as { result?: boolean };
      if (auth && auth.result === false) {
        throw new Error("Voximplant login failed");
      }
      setStatus("ready");
    } catch (err) {
      setStatus("idle");
      setError(err instanceof Error ? err.message : "Could not connect to Voximplant");
    } finally {
      setBusy(false);
    }
  }

  function answer() {
    const call = callRef.current;
    if (!call) {
      return;
    }
    setPlaying(false);
    call.answer("", {}, { sendVideo: false, receiveVideo: false });
    call.unmutePlayback();
    call.unmuteMicrophone();
    startPlaybackWatch(call);
    setStatus("in_call");
  }

  function hangup() {
    try {
      callRef.current?.hangup();
    } catch {
      // ignore
    }
    callRef.current = null;
    setStatus("ready");
    setPlaying(false);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Voice preview"
        title="Answer the recovery call here"
        description="The hosted Voximplant Web Softphone connects the call but does not play remote audio. This page uses the Web SDK on node2 and forces playback of the Gemini Live stream."
      />
      {error ? <ErrorAlert message={error} /> : null}
      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader
            title="Preview softphone"
            description="Close phone.voximplant.com first so this user is registered only here. Do not paste the password into chat."
          />
          <form className="space-y-4" onSubmit={connect}>
            <label className="block text-sm text-slate-700">
              Username
              <input
                readOnly
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
              App `{VOX_PREVIEW_APP}` · account `{VOX_PREVIEW_ACCOUNT}` · node `{VOX_PREVIEW_NODE}`
            </p>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={busy || status === "ready" || status === "incoming" || status === "in_call"}>
                {busy ? "Connecting…" : "Connect and wait"}
              </Button>
              {status === "incoming" ? (
                <Button onClick={answer} className="bg-emerald-600 hover:bg-emerald-700">
                  Answer
                </Button>
              ) : null}
              {status === "in_call" ? (
                <Button variant="danger" onClick={hangup}>
                  End call
                </Button>
              ) : null}
            </div>
          </form>
          <div
            id="eir-remote-media"
            ref={mediaRef}
            className="mt-4 min-h-12 rounded-xl bg-slate-50 p-3 text-sm text-slate-500"
          >
            Remote audio attaches here after you answer.
          </div>
        </Card>
        <Card>
          <CardHeader title="Status" />
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">SDK</dt>
              <dd className="font-medium text-slate-900">{status.replace("_", " ")}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Remote audio</dt>
              <dd className="font-medium text-slate-900">{playing ? "playing" : "not playing yet"}</dd>
            </div>
          </dl>
          <ol className="mt-5 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-600">
            <li>Close the Voximplant Web Softphone tab.</li>
            <li>Connect here and allow the microphone.</li>
            <li>Tell the agent to place the preview call.</li>
            <li>Press Answer. You should hear the EIR greeting, then speak naturally.</li>
          </ol>
        </Card>
      </div>
    </div>
  );
}
