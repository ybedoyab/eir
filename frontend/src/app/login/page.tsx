"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon, type IconName } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { APP_META, APP_ROUTES } from "@/config/app";
import { roleHome, saveSession } from "@/lib/auth";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { DEMO_PERSONAS, roleLabel } from "@/lib/personas";
import { listDemoUsers, loginDemo } from "@/services/api";

interface DemoUser {
  username: string;
  display_name: string;
  role: string;
  password_hint: string;
}

interface LoginUser extends DemoUser {
  description: string;
}

const ROLE_ICONS: Record<string, IconName> = {
  PATIENT: "heart",
  CLINICIAN: "recovery",
  OPERATIONS_ADMIN: "overview",
};

function RoleCard({
  user,
  busy,
  onSignIn,
}: {
  user: LoginUser;
  busy: boolean;
  onSignIn: (user: LoginUser) => void;
}) {
  return (
    <article className="eir-surface eir-card-hover group flex h-full flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <Avatar name={user.display_name} size="lg" />
        <span className="eir-icon-shell h-10 w-10">
          <Icon name={ROLE_ICONS[user.role] ?? "patients"} size={18} />
        </span>
      </div>
      <span className="mt-5 font-mono text-[0.68rem] font-medium uppercase tracking-[0.12em] text-accent">
        {roleLabel(user.role)}
      </span>
      <h2 className="mt-1.5 text-[1.08rem] font-semibold text-ink">{user.display_name}</h2>
      <p className="mt-2 flex-1 text-[0.84rem] leading-[1.6] text-secondary">{user.description}</p>
      <Button className="mt-5 w-full" disabled={busy} onClick={() => onSignIn(user)}>
        {busy ? "Signing in…" : "Enter workspace"}
        <Icon name="arrowRight" size={16} />
      </Button>
    </article>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void listDemoUsers()
      .then(setUsers)
      .catch((requestError) => setError(getErrorMessage(requestError, ERROR_MESSAGES.demoUsers)))
      .finally(() => setLoading(false));
  }, []);

  const { primary, secondary } = useMemo(() => {
    const mapped = users.map((user) => ({
      ...user,
      description: DEMO_PERSONAS[user.username]?.description ?? "Explore this workspace.",
      primary: DEMO_PERSONAS[user.username]?.primary ?? true,
    }));
    return {
      primary: mapped.filter((user) => user.primary).slice(0, 3),
      secondary: mapped.filter((user) => !user.primary),
    };
  }, [users]);

  async function signIn(user: LoginUser) {
    setBusy(user.username);
    setError(null);
    try {
      const session = await loginDemo(user.username, user.password_hint);
      saveSession(session);
      router.push(roleHome(session.role));
    } catch {
      setError(ERROR_MESSAGES.login);
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="eir-page relative min-h-screen overflow-hidden px-5 py-7 sm:px-8 lg:px-12">
      <span className="eir-orb eir-drift pointer-events-none absolute -left-20 top-32 h-64 w-64 opacity-10" aria-hidden />
      <span className="eir-orb eir-drift pointer-events-none absolute -right-16 -top-20 h-48 w-48 opacity-[0.08]" aria-hidden />

      <div className="mx-auto max-w-[1240px]">
        <Link href={APP_ROUTES.home} className="focus-ink group inline-flex items-center gap-3 rounded-xl">
          <span className="eir-icon-shell h-10 w-10"><Logo size={23} /></span>
          <span className="font-serif text-[1.25rem] font-semibold text-ink">{APP_META.name}</span>
          <span className="h-4 w-px bg-rule-strong" aria-hidden />
          <span className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted">Demo access</span>
        </Link>

        <div className="mt-10 grid gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-start lg:gap-16">
          <section className="eir-enter lg:sticky lg:top-10">
            <span className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-surface/70 px-3 py-1.5 font-mono text-[0.68rem] uppercase tracking-[0.1em] text-accent">
              <Icon name="shield" size={14} />
              Secure demo identities
            </span>
            <h1 className="mt-6 max-w-[10ch] font-serif text-[2.65rem] font-semibold leading-[1.06] tracking-[-0.025em] text-ink sm:text-[3.45rem]">
              Choose your view of the hospital.
            </h1>
            <p className="mt-5 max-w-[34rem] text-[1rem] leading-[1.7] text-secondary">
              Enter as a patient, clinician or operations lead. Each workspace uses the same live workflows with tools shaped for the role.
            </p>
            <div className="eir-surface-soft mt-8 flex flex-col gap-4 p-4">
              <span className="flex items-start gap-3"><span className="eir-icon-shell h-9 w-9 rounded-lg"><Icon name="activity" size={16} /></span><span><span className="block text-[0.84rem] font-semibold text-ink">Live operational data</span><span className="block text-[0.75rem] text-muted">Connected to the local API</span></span></span>
              <span className="flex items-start gap-3"><span className="eir-icon-shell h-9 w-9 rounded-lg"><Icon name="shield" size={16} /></span><span><span className="block text-[0.84rem] font-semibold text-ink">Safe by design</span><span className="block text-[0.75rem] text-muted">All people and records are fictional</span></span></span>
            </div>
          </section>

          <section className="min-w-0">
            <div className="mb-6 flex items-end justify-between gap-4">
              <div>
                <span className="font-mono text-[0.68rem] font-medium uppercase tracking-[0.12em] text-accent">Available workspaces</span>
                <h2 className="mt-2 font-serif text-[1.65rem] font-medium text-ink">Sign in to EIR</h2>
              </div>
              <span className="eir-status-dot" aria-label="API online" />
            </div>

            {error ? <ErrorAlert message={error} /> : null}

            {loading ? (
              <CardSkeleton rows={6} />
            ) : (
              <div className="eir-stagger grid gap-4 sm:grid-cols-3">
                {primary.map((user) => (
                  <RoleCard key={user.username} user={user} busy={busy === user.username} onSignIn={(selected) => void signIn(selected)} />
                ))}
              </div>
            )}

            {secondary.length ? (
              <div className="eir-surface mt-5 flex flex-wrap items-center justify-between gap-4 p-4">
                {secondary.map((user) => (
                  <span key={user.username} className="flex min-w-0 items-center gap-3">
                    <Avatar name={user.display_name} size="sm" />
                    <span className="min-w-0"><span className="block truncate text-[0.9rem] font-semibold text-ink">{user.display_name}</span><span className="block truncate text-[0.75rem] text-muted">{user.description}</span></span>
                  </span>
                ))}
                <Button variant="secondary" disabled={busy === secondary[0].username} onClick={() => void signIn(secondary[0])}>
                  Continue
                  <Icon name="arrowRight" size={15} />
                </Button>
              </div>
            ) : null}

            <p className="mt-7 text-[0.82rem] text-secondary">
              Prefer the guided story? <Link href={APP_ROUTES.demo} className="focus-ink rounded-md font-semibold text-accent hover:text-ink">Open the live recovery demo</Link>
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
