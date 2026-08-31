import Link from "next/link";

import { ActionLink } from "@/components/ui/ActionLink";
import { Icon, type IconName } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { APP_META, APP_ROUTES } from "@/config/app";

interface CascadeRow {
  at: string;
  event: string;
  capability: string;
  outcome: string;
  tone: string;
}

interface Capability {
  index: string;
  title: string;
  body: string;
  capabilities: string[];
  icon: IconName;
}

const CASCADE: CascadeRow[] = [
  {
    at: "14:22:07.3",
    event: "FollowUpDue",
    capability: "patient.contact",
    outcome: "handled",
    tone: "text-ok",
  },
  {
    at: "14:22:07.9",
    event: "PatientResponded",
    capability: "risk.assess",
    outcome: "MEDIUM",
    tone: "text-warn",
  },
  {
    at: "14:22:08.1",
    event: "RiskEscalated",
    capability: "care.escalate",
    outcome: "HIGH",
    tone: "text-high",
  },
];

const CAPABILITIES: Capability[] = [
  {
    index: "01",
    title: "Patient Access",
    body: "Appointments, reminders and a hospital assistant that routes on deterministic intent rules. Clinical symptoms and injection attempts never reach the model's judgement.",
    capabilities: ["appointment.read", "appointment.schedule", "patient.assist"],
    icon: "patients",
  },
  {
    index: "02",
    title: "Recovery",
    body: "Longitudinal follow-up over days, with scheduled check-ins, risk assessment on every response and a clinician in the loop when risk rises.",
    capabilities: ["patient.contact", "risk.assess", "care.escalate"],
    icon: "heart",
  },
  {
    index: "03",
    title: "Hospital Operations",
    body: "A command center for schedules, pending reviews and the fleet itself, including which adapters are live and which are using a fallback.",
    capabilities: ["records.read", "human.handoff", "care.task.follow_up"],
    icon: "overview",
  },
];

const PLATFORM = [
  { name: "Gemini", detail: "language + tool calling", icon: "sparkles" },
  { name: "ADK", detail: "required-tool contract", icon: "activity" },
  { name: "Agent Runtime", detail: "managed access agent", icon: "server" },
  { name: "Memory Bank", detail: "allowlisted keys only", icon: "shield" },
  { name: "Agent Gateway", detail: "ingress inspection", icon: "fleet" },
  { name: "Model Armor", detail: "prompt-injection block", icon: "shield" },
  { name: "FHIR R4", detail: "demo patient records", icon: "recovery" },
] satisfies Array<{ name: string; detail: string; icon: IconName }>;

function BrandHeader() {
  return (
    <header className="eir-glass sticky top-0 z-40 border-b border-rule/80 px-5 sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-5 py-3">
        <Link href={APP_ROUTES.home} className="focus-ink group flex items-center gap-3 rounded-xl">
          <span className="eir-icon-shell h-10 w-10 rounded-xl">
            <Logo size={23} />
          </span>
          <span className="flex flex-col sm:flex-row sm:items-center sm:gap-3">
            <span className="font-serif text-[1.35rem] font-semibold tracking-[-0.01em] text-ink">
              {APP_META.name}
            </span>
            <span className="hidden h-4 w-px bg-rule-strong sm:block" aria-hidden />
            <span className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted">
              {APP_META.longName}
            </span>
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <ActionLink href={APP_ROUTES.login} variant="ghost" className="px-4">
            Sign in
          </ActionLink>
          <ActionLink href={APP_ROUTES.demo}>
            Open live demo
            <Icon name="arrowRight" size={16} />
          </ActionLink>
        </div>
      </div>
    </header>
  );
}

function RuntimePreview() {
  return (
    <div className="eir-enter relative lg:col-span-5">
      <span className="eir-orb eir-drift absolute -right-4 -top-10 h-24 w-24 opacity-50" aria-hidden />
      <div className="eir-surface relative overflow-hidden p-5 sm:p-6">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-accent via-accent-bright to-teal" aria-hidden />
        <div className="flex items-center justify-between gap-4 border-b border-rule pb-4">
          <span className="flex items-center gap-2.5 font-mono text-[0.72rem] font-medium uppercase tracking-[0.1em] text-secondary">
            <span className="eir-status-dot" aria-hidden />
            Recovery episode · live
          </span>
          <span className="rounded-full bg-accent-tint px-2.5 py-1 font-mono text-[0.68rem] text-accent">
            depth 4 / 12
          </span>
        </div>

        <div className="eir-stagger mt-2 flex flex-col">
          {CASCADE.map((row) => (
            <div
              key={row.event}
              className="eir-list-row grid grid-cols-[80px_minmax(0,1fr)_68px] items-center gap-3 px-2 py-3.5 font-mono text-[0.72rem]"
            >
              <span className="text-muted">{row.at}</span>
              <span className="min-w-0">
                <span className="block truncate font-medium text-ink">{row.event}</span>
                <span className="block truncate text-muted">{row.capability}</span>
              </span>
              <span className={`text-right ${row.tone}`}>{row.outcome}</span>
            </div>
          ))}
        </div>

        <div className="eir-cut eir-halt mt-3 flex items-center gap-3 rounded-xl border border-high/30 bg-ink px-4 py-3.5">
          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-high text-paper">
            <Icon name="halt" size={16} />
          </span>
          <span className="min-w-0">
            <span className="block font-mono text-[0.7rem] font-semibold tracking-[0.1em] text-paper">
              CASCADE HALTED
            </span>
            <span className="mt-0.5 block text-[0.78rem] leading-snug text-on-ink">
              Waiting for clinician approval before the workflow continues.
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}

function CapabilityCard({ capability }: { capability: Capability }) {
  return (
    <article className="eir-surface eir-card-hover group flex h-full flex-col p-6">
      <div className="flex items-center justify-between">
        <span className="eir-icon-shell h-11 w-11">
          <Icon name={capability.icon} size={20} />
        </span>
        <span className="font-mono text-[0.7rem] text-muted">{capability.index}</span>
      </div>
      <h3 className="mt-6 font-serif text-[1.45rem] font-medium tracking-[-0.01em] text-ink">
        {capability.title}
      </h3>
      <p className="mt-3 flex-1 text-[0.9rem] leading-[1.65] text-secondary">{capability.body}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {capability.capabilities.map((item) => (
          <span key={item} className="rounded-full border border-rule bg-raised/70 px-2.5 py-1 font-mono text-[0.66rem] text-muted">
            {item}
          </span>
        ))}
      </div>
    </article>
  );
}

export default function HomePage() {
  return (
    <div className="eir-page flex min-h-screen flex-col overflow-hidden">
      <div className="eir-progress" aria-hidden />
      <BrandHeader />

      <main>
        <section className="relative px-5 pb-20 pt-16 sm:px-8 lg:px-12 lg:pb-24 lg:pt-24">
          <span className="eir-orb eir-drift pointer-events-none absolute -left-20 top-8 h-56 w-56 opacity-[0.08]" aria-hidden />
          <div className="mx-auto grid max-w-[1320px] gap-14 lg:grid-cols-12 lg:items-center">
            <div className="eir-enter lg:col-span-7">
              <span className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-surface/70 px-3.5 py-2 font-mono text-[0.7rem] font-medium uppercase tracking-[0.1em] text-accent shadow-[0_5px_18px_rgb(22_75_130/0.08)]">
                <Icon name="sparkles" size={14} />
                Observable healthcare automation
              </span>
              <h1 className="mt-7 max-w-[13ch] font-serif text-[2.8rem] font-semibold leading-[1.03] tracking-[-0.03em] text-ink sm:text-[4.25rem]">
                A hospital fleet you can see, trust and guide.
              </h1>
              <p className="mt-6 max-w-[38rem] text-[1.05rem] leading-[1.7] text-secondary sm:text-[1.12rem]">
                EIR coordinates patient access, recovery follow-up and clinical review across seven agents. Every routing decision, safety gate and human handoff stays visible.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <ActionLink href={APP_ROUTES.demo} className="min-h-12 px-6 text-[0.95rem]">
                  Explore the live workflow
                  <Icon name="arrowRight" size={16} />
                </ActionLink>
                <ActionLink href={APP_ROUTES.login} variant="secondary" className="min-h-12 px-6 text-[0.95rem]">
                  <Icon name="patients" size={16} />
                  Sign in by role
                </ActionLink>
              </div>
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-[0.78rem] text-muted">
                <span className="inline-flex items-center gap-2"><Icon name="shield" size={15} className="text-ok" />Guarded by policy</span>
                <span className="inline-flex items-center gap-2"><Icon name="observe" size={15} className="text-accent" />Fully observable</span>
                <span className="inline-flex items-center gap-2"><Icon name="patients" size={15} className="text-teal" />Human in the loop</span>
              </div>
            </div>
            <RuntimePreview />
          </div>
        </section>

        <section className="px-5 pb-20 sm:px-8 lg:px-12 lg:pb-24">
          <div className="mx-auto max-w-[1320px]">
            <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="font-mono text-[0.7rem] font-medium uppercase tracking-[0.12em] text-accent">Fleet coverage</span>
                <h2 className="mt-2 font-serif text-[2rem] font-medium tracking-[-0.02em] text-ink">One coordinated operating layer</h2>
              </div>
              <span className="rounded-full border border-rule bg-surface/60 px-3 py-1.5 font-mono text-[0.7rem] text-muted">7 agents · capability-routed</span>
            </div>
            <div className="eir-stagger grid gap-5 md:grid-cols-3">
              {CAPABILITIES.map((capability) => <CapabilityCard key={capability.index} capability={capability} />)}
            </div>
          </div>
        </section>

        <section className="px-5 pb-20 sm:px-8 lg:px-12 lg:pb-24">
          <div className="eir-surface mx-auto max-w-[1320px] overflow-hidden p-6 sm:p-8">
            <div className="flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-5">
              <div>
                <span className="font-mono text-[0.7rem] font-medium uppercase tracking-[0.12em] text-accent">Managed platform</span>
                <h2 className="mt-2 font-serif text-[1.75rem] font-medium text-ink">Designed for a guarded runtime</h2>
              </div>
              <Link href={APP_ROUTES.admin.fleet} className="focus-ink group inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-medium text-accent hover:bg-accent-tint">
                Live adapter status
                <Icon name="arrowRight" size={14} />
              </Link>
            </div>
            <div className="eir-stagger mt-2 grid sm:grid-cols-2 lg:grid-cols-4">
              {PLATFORM.map((item) => (
                <div key={item.name} className="eir-list-row group flex items-center gap-3 px-3 py-5">
                  <span className="eir-icon-shell h-9 w-9 rounded-lg"><Icon name={item.icon} size={16} /></span>
                  <span className="min-w-0"><span className="block text-[0.9rem] font-semibold text-ink">{item.name}</span><span className="block truncate font-mono text-[0.66rem] text-muted">{item.detail}</span></span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="mt-auto border-t border-rule/80 bg-raised/70 px-5 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-5 py-5">
          <span className="font-mono text-[0.7rem] text-muted">{APP_META.environmentNote}</span>
          <div className="flex flex-wrap gap-5 text-[0.78rem]">
            <Link href={APP_ROUTES.agents} className="focus-ink rounded-lg px-2 py-1 text-accent hover:bg-accent-tint">Architecture</Link>
            <Link href={APP_ROUTES.admin.fleet} className="focus-ink rounded-lg px-2 py-1 text-accent hover:bg-accent-tint">Adapter status</Link>
            <Link href={APP_ROUTES.login} className="focus-ink rounded-lg px-2 py-1 text-accent hover:bg-accent-tint">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
