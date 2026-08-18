import Link from "next/link";

import { Card } from "@/components/ui/Card";

const modules = [
  {
    title: "Patient Access",
    description: "Appointments, assistant chat, and portal self-service.",
    href: "/login",
    tone: "bg-teal-50 text-teal-700",
  },
  {
    title: "Recovery",
    description: "Longitudinal follow-up, voice outreach, and clinician review.",
    href: "/demo",
    tone: "bg-sky-50 text-sky-700",
  },
  {
    title: "Clinical Reviews",
    description: "Escalations, human review queue, and patient charts.",
    href: "/login",
    tone: "bg-violet-50 text-violet-700",
  },
  {
    title: "Fleet Operations",
    description: "Agent registry, observability, and synthetic hospital metrics.",
    href: "/login",
    tone: "bg-amber-50 text-amber-700",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/80 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-700 text-sm font-semibold text-white">
              E
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-900">EIR</p>
              <p className="text-xs text-slate-500">Healthcare Agent Fleet</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href="/login" className="rounded-lg px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
              Sign in
            </Link>
            <Link href="/demo" className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800">
              Live demo
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
        <section className="overflow-hidden rounded-[28px] border border-teal-100 bg-gradient-to-br from-white via-teal-50/60 to-slate-50 px-6 py-10 shadow-[var(--eir-shadow)] sm:px-10 sm:py-12">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700">
            Enterprise Intelligence Runtime
          </p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            AI-powered hospital operations across voice and web.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
            EIR coordinates patient access, appointment lifecycle, recovery follow-up, and staff
            workspaces through one secure agent fleet. Synthetic demo data only.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/login" className="rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-teal-800">
              Enter portal
            </Link>
            <Link href="/dev/voice-preview" className="rounded-lg bg-white px-4 py-2.5 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50">
              Developer voice preview
            </Link>
          </div>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-semibold text-slate-900">Product modules</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {modules.map((module) => (
              <Link key={module.title} href={module.href}>
                <Card className="h-full transition hover:border-teal-200 hover:shadow-lg">
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${module.tone}`}>
                    {module.title}
                  </span>
                  <h3 className="mt-4 text-lg font-semibold text-slate-900">{module.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{module.description}</p>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
