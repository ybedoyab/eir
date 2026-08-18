"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import type { AdminSnapshot } from "@/lib/auth";
import { getAdminSnapshot, listAgents, listRecovery, listReviews } from "@/services/api";
import type { AgentDescriptor } from "@/types";

export default function AdminHomePage() {
  const [snapshot, setSnapshot] = useState<AdminSnapshot | null>(null);
  const [agents, setAgents] = useState<AgentDescriptor[]>([]);
  const [recoveries, setRecoveries] = useState(0);
  const [reviews, setReviews] = useState(0);

  useEffect(() => {
    void Promise.all([getAdminSnapshot(), listAgents(), listRecovery(), listReviews(true)]).then(
      ([snap, agentItems, episodeItems, reviewItems]) => {
        setSnapshot(snap);
        setAgents(agentItems);
        setRecoveries(episodeItems.filter((item) => item.status !== "COMPLETED").length);
        setReviews(reviewItems.length);
      },
    );
  }, []);

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Operations"
        title="Hospital Operations Command Center"
        description="Metrics computed from synthetic stored data only."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Today's appointments", snapshot?.appointments.today_appointments ?? 0],
          ["Open slots", snapshot?.appointments.open_slots ?? 0],
          ["Active recoveries", recoveries],
          ["Human reviews waiting", reviews],
        ].map(([label, value]) => (
          <Card key={label}>
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader title="Fleet status" description="Registered agents and capabilities." />
        <div className="grid gap-3 md:grid-cols-2">
          {agents.map((agent) => (
            <div key={agent.name} className="rounded-xl border border-slate-200 p-4">
              <p className="font-medium text-slate-900">{agent.name}</p>
              <p className="mt-1 text-sm text-slate-600">{agent.description}</p>
              <p className="mt-2 text-xs text-slate-500">{agent.capabilities.join(", ")}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/admin/fleet" className="text-sm font-medium text-teal-700">
            Fleet details
          </Link>
          <Link href="/admin/observability" className="text-sm font-medium text-teal-700">
            Observability
          </Link>
          <Link href="/demo" className="text-sm font-medium text-teal-700">
            Recovery demo
          </Link>
        </div>
      </Card>
    </section>
  );
}
