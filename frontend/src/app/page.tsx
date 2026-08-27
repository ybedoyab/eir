import Link from "next/link";

import { Icon } from "@/components/ui/Icon";

interface CascadeRow {
  at: string;
  event: string;
  capability: string;
  outcome: string;
  tone: string;
  delay: string;
}

/** A real follow-up run: scheduler -> outreach -> risk -> a halt. */
const cascade: CascadeRow[] = [
  {
    at: "14:22:07.3",
    event: "FollowUpDue",
    capability: "patient.contact",
    outcome: "handled",
    tone: "text-ok",
    delay: "240ms",
  },
  {
    at: "14:22:07.9",
    event: "PatientResponded",
    capability: "risk.assess",
    outcome: "MEDIUM",
    tone: "text-warn",
    delay: "340ms",
  },
  {
    at: "14:22:08.1",
    event: "RiskEscalated",
    capability: "care.escalate",
    outcome: "HIGH",
    tone: "text-high",
    delay: "440ms",
  },
];

const ledger = [
  {
    index: "01",
    title: "Patient Access",
    body: "Appointments, reminders and a hospital assistant that routes on deterministic intent rules — clinical symptoms and injection attempts never reach the model's judgement.",
    capabilities: ["appointment.read", "appointment.schedule", "patient.assist"],
  },
  {
    index: "02",
    title: "Recovery",
    body: "Longitudinal follow-up over days, not one session. Scheduled check-ins, risk assessment on each response, and a clinician in the loop the moment risk rises.",
    capabilities: ["patient.contact", "risk.assess", "care.escalate"],
  },
  {
    index: "03",
    title: "Hospital Operations",
    body: "A command center for schedules, pending reviews and the fleet itself — including which adapters are running for real and which are degraded to a fallback.",
    capabilities: ["records.read", "human.handoff", "care.task.follow_up"],
  },
];

const platform = [
  { name: "Gemini", detail: "language + tool calling" },
  { name: "ADK", detail: "required-tool contract" },
  { name: "Agent Runtime", detail: "managed access agent" },
  { name: "Memory Bank", detail: "allowlisted keys only" },
  { name: "Agent Gateway", detail: "ingress inspection" },
  { name: "Model Armor", detail: "prompt-injection block" },
  { name: "FHIR R4", detail: "synthetic records" },
];

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <div className="eir-progress" aria-hidden />

      <header className="flex flex-wrap items-center justify-between gap-6 border-b border-rule px-6 py-5 sm:px-10 lg:px-16">
        <div className="flex items-center gap-4">
          <span className="font-serif text-[1.4375rem] font-semibold tracking-[-0.01em] text-ink">
            EIR
          </span>
          <span className="h-5 w-px bg-rule-strong" aria-hidden />
          <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-muted">
            Enterprise Intelligence Runtime
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="focus-ink inline-flex min-h-11 items-center px-4 text-sm font-medium text-body hover:text-ink"
          >
            Sign in
          </Link>
          <Link
            href="/demo"
            className="focus-ink inline-flex min-h-11 items-center gap-2.5 bg-accent px-5 text-sm font-medium text-paper hover:bg-accent-hover"
          >
            Open the live demo
            <Icon name="arrowRight" size={16} />
          </Link>
        </div>
      </header>

      {/* hero + the runtime strip: the product, on the front page */}
      <section className="grid gap-12 px-6 pb-16 pt-16 sm:px-10 lg:grid-cols-12 lg:px-16 lg:pb-[68px] lg:pt-[76px]">
        <div className="eir-enter lg:col-span-7">
          <h1 className="font-serif text-[2.5rem] font-semibold leading-[1.06] tracking-[-0.022em] text-ink sm:text-[3.625rem]">
            Hospital operations run by a fleet you can watch.
          </h1>
          <p className="mt-6 max-w-[30em] text-[1.0625rem] leading-[1.62] text-secondary">
            EIR coordinates patient access, recovery follow-up and clinical review across seven
            agents. Every routing decision, safety gate and halt is on screen — not buried in a
            log.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href="/demo"
              className="focus-ink inline-flex min-h-11 items-center gap-2.5 bg-accent px-6 text-[0.9375rem] font-medium text-paper hover:bg-accent-hover"
            >
              Open the live demo
              <Icon name="arrowRight" size={16} />
            </Link>
            <Link
              href="/login"
              className="focus-ink inline-flex min-h-11 items-center gap-2.5 border border-rule-strong px-6 text-[0.9375rem] font-medium text-body hover:bg-hover"
            >
              Sign in by role
              <Icon name="chevronRight" size={15} className="text-muted" />
            </Link>
          </div>
          <p className="mt-7 font-mono text-[0.75rem] leading-snug text-muted">
            Every identity and record in this environment is synthetic.
          </p>
        </div>

        <div
          className="eir-enter flex flex-col lg:col-span-5"
          style={{ animationDelay: "110ms" }}
        >
          <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
            <span className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-secondary">
              Recovery episode · live
            </span>
            <span className="font-mono text-[0.75rem] tracking-[0.06em] text-muted">depth 4 / 12</span>
          </div>

          <div className="flex flex-col">
            {cascade.map((row) => (
              <div
                key={row.event}
                className="eir-enter grid grid-cols-[92px_minmax(0,1fr)_132px_74px] items-center gap-3 border-b border-rule py-[13px] font-mono text-[12.5px]"
                style={{ animationDelay: row.delay }}
              >
                <span className="text-muted">{row.at}</span>
                <span className="truncate text-ink">{row.event}</span>
                <span className="truncate text-secondary">{row.capability}</span>
                <span className={`text-right ${row.tone}`}>{row.outcome}</span>
              </div>
            ))}

            {/* the halt: register changes, no hue, no motion */}
            <div className="eir-cut eir-halt mt-3.5 flex items-center gap-4 border-l-[3px] border-high bg-ink px-[18px] py-4">
              <span className="inline-flex items-center gap-2 font-mono text-[0.75rem] font-medium tracking-[0.12em] text-paper">
                <Icon name="halt" size={14} />
                CASCADE HALTED
              </span>
              <span className="text-[0.8125rem] leading-snug text-on-ink">
                Blocking capability parked the workflow for human approval.
              </span>
            </div>
            <p className="eir-cut mt-3.5 text-[0.8125rem] leading-relaxed text-muted">
              The runtime stops here until a clinician answers. Nothing downstream runs in the
              meantime.
            </p>
          </div>
        </div>
      </section>

      {/* capability ledger — numbered rows, not three-across pillar cards */}
      <section className="px-6 pb-[72px] sm:px-10 lg:px-16">
        <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-3">
          <h2 className="font-mono text-[0.75rem] font-medium uppercase tracking-[0.1em] text-secondary">
            What the fleet covers
          </h2>
          <span className="font-mono text-[0.75rem] tracking-[0.06em] text-muted">
            7 agents · capability-routed
          </span>
        </div>

        <div className="flex flex-col">
          {ledger.map((item) => (
            <div
              key={item.index}
              className="eir-reveal grid gap-6 border-b border-rule py-[30px] lg:grid-cols-[56px_300px_minmax(0,1fr)_260px] lg:gap-8"
            >
              <span className="font-mono text-[0.8125rem] text-muted">{item.index}</span>
              <h3 className="font-serif text-[1.5625rem] font-medium tracking-[-0.01em] text-ink">
                {item.title}
              </h3>
              <p className="text-[0.9375rem] leading-[1.65] text-secondary">{item.body}</p>
              <div className="flex flex-col gap-1.5 font-mono text-[0.75rem] text-muted">
                {item.capabilities.map((capability) => (
                  <span key={capability}>{capability}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* managed platform */}
      <section className="px-6 pb-[76px] sm:px-10 lg:px-16">
        <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-3">
          <h2 className="font-mono text-[0.75rem] font-medium uppercase tracking-[0.1em] text-secondary">
            Managed platform
          </h2>
          <Link
            href="/admin/fleet"
            className="focus-ink -my-3 inline-flex min-h-11 items-center gap-2 font-mono text-[0.75rem] tracking-[0.06em] text-accent hover:text-ink"
          >
            Live adapter status
            <Icon name="arrowRight" size={13} />
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 [&>*]:border-b [&>*]:border-rule [&>*]:px-6 sm:[&>*]:border-r sm:[&>*:nth-child(2n)]:border-r-0 sm:[&>*:nth-child(2n+1)]:pl-0 lg:[&>*:nth-child(2n)]:border-r lg:[&>*:nth-child(2n+1)]:pl-6 lg:[&>*:nth-child(4n)]:border-r-0 lg:[&>*:nth-child(4n+1)]:pl-0">
          {platform.map((item) => (
            <div key={item.name} className="eir-reveal flex flex-col gap-1 py-[22px]">
              <span className="text-[0.9375rem] font-medium text-ink">{item.name}</span>
              <span className="font-mono text-[0.75rem] text-muted">{item.detail}</span>
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-6 border-t border-rule bg-raised px-6 py-3 sm:px-10 lg:px-16">
        <span className="font-mono text-[11.5px] text-muted">
          Synthetic demo environment · no real patient data
        </span>
        <div className="flex flex-wrap gap-6 font-mono text-[11.5px]">
          <Link
            href="/agents"
            className="focus-ink inline-flex min-h-11 items-center text-accent hover:text-ink"
          >
            Architecture
          </Link>
          <Link
            href="/admin/fleet"
            className="focus-ink inline-flex min-h-11 items-center text-accent hover:text-ink"
          >
            Adapter status
          </Link>
          <Link
            href="/login"
            className="focus-ink inline-flex min-h-11 items-center text-accent hover:text-ink"
          >
            Sign in
          </Link>
        </div>
      </footer>
    </div>
  );
}
