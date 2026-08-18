"use client";

import dynamic from "next/dynamic";

const VoicePreviewClient = dynamic(() => import("./VoicePreviewClient"), {
  ssr: false,
  loading: () => <p className="text-sm text-slate-600">Loading voice preview…</p>,
});

export default function VoicePreviewPage() {
  return <VoicePreviewClient />;
}
