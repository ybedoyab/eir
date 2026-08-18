import { CalendarDays, HeartPulse, MessageCircle } from "lucide-react";
import Link from "next/link";

const pillars = [
  {
    title: "Patient Access",
    description: "Appointments, reminders, and a secure hospital assistant.",
    icon: CalendarDays,
  },
  {
    title: "Recovery",
    description: "Longitudinal follow-up with clinician review when risk rises.",
    icon: HeartPulse,
  },
  {
    title: "Hospital Operations",
    description: "A command center for schedules, reviews, and the agent fleet.",
    icon: MessageCircle,
  },
];

const platform = [
  "Gemini",
  "ADK",
  "Agent Runtime",
  "Memory Bank",
  "Agent Gateway",
  "Model Armor",
  "FHIR",
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
            <Link
              href="/login"
              className="inline-flex min-h-11 items-center rounded-lg px-4 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Sign in
            </Link>
            <Link
              href="/demo"
              className="inline-flex min-h-11 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
            >
              Live demo
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
        <section className="rounded-[28px] border border-teal-100 bg-white px-6 py-10 shadow-[var(--eir-shadow)] sm:px-10 sm:py-12">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700">
            Healthcare Agent Fleet
          </p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            One secure agent fleet for hospital access, recovery, and operations.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
            EIR coordinates patient access, recovery follow-up, and staff workspaces through
            managed Google agent infrastructure. Synthetic demo identities only.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/demo"
              className="inline-flex min-h-11 items-center rounded-lg bg-teal-700 px-4 text-sm font-medium text-white hover:bg-teal-800"
            >
              Explore live demo
            </Link>
            <Link
              href="/login"
              className="inline-flex min-h-11 items-center rounded-lg bg-white px-4 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            >
              Sign in by role
            </Link>
          </div>
        </section>

        <section className="mt-10 grid gap-4 md:grid-cols-3">
          {pillars.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <div
                key={pillar.title}
                className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[var(--eir-shadow)]"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-800">
                  <Icon aria-hidden className="h-5 w-5" />
                </span>
                <h2 className="mt-4 text-lg font-semibold text-slate-900">{pillar.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{pillar.description}</p>
              </div>
            );
          })}
        </section>

        <section className="mt-10 rounded-2xl border border-slate-200 bg-slate-50/80 px-5 py-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Managed platform
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {platform.map((item) => (
              <span
                key={item}
                className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200"
              >
                {item}
              </span>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
