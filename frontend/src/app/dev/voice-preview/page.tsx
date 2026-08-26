"use client";

import dynamic from "next/dynamic";

import { PageHeader } from "@/components/ui/PageHeader";

const VoicePreviewClient = dynamic(() => import("../../voice-preview/VoicePreviewClient"), {
  ssr: false,
  loading: () => <p className="text-sm text-slate-600">Loading voice preview…</p>,
});

export default function DevVoicePreviewPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Developer"
        title="Voice check-in"
        description="Browser-dialled WebRTC check-in against the live Voximplant scenario. Transcript is ephemeral and stays in this tab; the structured result reaches the episode through the callback."
      />
      <VoicePreviewClient />
    </section>
  );
}
