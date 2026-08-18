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
        title="Voice preview"
        description="Ephemeral browser transcript only. No paid PSTN/WebRTC verification this sprint."
      />
      <VoicePreviewClient />
    </section>
  );
}
