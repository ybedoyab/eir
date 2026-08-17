import Link from "next/link";

import { Card } from "@/components/ui/Card";

const sections = [
  {
    href: "/patients",
    title: "Patients",
    description: "Browse synthetic patient profiles and start recovery episodes.",
    tone: "bg-sky-50 text-sky-700",
  },
  {
    href: "/recovery",
    title: "Recovery",
    description: "Track episode status, risk levels, and pending human reviews.",
    tone: "bg-teal-50 text-teal-700",
  },
  {
    href: "/agents",
    title: "Agents",
    description: "Inspect the recovery fleet registry and agent capabilities.",
    tone: "bg-violet-50 text-violet-700",
  },
  {
    href: "/observability",
    title: "Observability",
    description: "Follow workflow traces across outreach, risk, and safety gates.",
    tone: "bg-amber-50 text-amber-700",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="overflow-hidden rounded-[28px] border border-teal-100 bg-gradient-to-br from-white via-teal-50/60 to-slate-50 px-6 py-10 shadow-[var(--eir-shadow)] sm:px-10 sm:py-12">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-teal-700">
          Enterprise Intelligence for Recovery
        </p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          A secure autonomous recovery fleet for healthcare.
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
          Coordinate follow-ups, risk assessment, and human review with synthetic data only.
          Built for safe demos and production-ready GCP adapters.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/recovery"
            className="inline-flex items-center rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-teal-800"
          >
            Open recovery dashboard
          </Link>
          <Link
            href="/patients"
            className="inline-flex items-center rounded-lg bg-white px-4 py-2.5 text-sm font-medium text-slate-700 ring-1 ring-slate-200 transition hover:bg-slate-50"
          >
            View patients
          </Link>
        </div>
      </section>

      <section>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Workspace</h2>
          <p className="mt-1 text-sm text-slate-500">Jump into the main operational views.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {sections.map((section) => (
            <Link key={section.href} href={section.href} className="group">
              <Card className="h-full transition group-hover:-translate-y-0.5 group-hover:border-teal-200 group-hover:shadow-lg">
                <span
                  className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${section.tone}`}
                >
                  {section.title}
                </span>
                <h3 className="mt-4 text-lg font-semibold text-slate-900 group-hover:text-teal-800">
                  {section.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
