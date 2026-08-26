"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { roleHome, saveSession } from "@/lib/auth";
import { DEMO_PERSONAS, roleLabel } from "@/lib/personas";
import { listDemoUsers, loginDemo } from "@/services/api";

export default function LoginPage() {
  const router = useRouter();
  const [users, setUsers] = useState<
    Array<{ username: string; display_name: string; role: string; password_hint: string }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void listDemoUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load demo users"))
      .finally(() => setLoading(false));
  }, []);

  const { primary, secondary } = useMemo(() => {
    const mapped = users.map((user) => ({
      ...user,
      copy: DEMO_PERSONAS[user.username],
    }));
    return {
      primary: mapped.filter((user) => user.copy?.primary !== false).slice(0, 3),
      secondary: mapped.filter((user) => user.copy?.primary === false),
    };
  }, [users]);

  async function signIn(username: string, password: string) {
    setBusy(username);
    setError(null);
    try {
      const session = await loginDemo(username, password);
      saveSession(session);
      router.push(roleHome(session.role));
    } catch {
      setError("Sign in failed. Use the demo password shown for each role.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <div className="mb-8 flex items-center gap-4 border-b border-rule pb-5">
        <span className="font-serif text-[20px] font-semibold tracking-[-0.01em] text-ink">
          EIR
        </span>
        <span className="h-[15px] w-px bg-rule-strong" aria-hidden />
        <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
          Synthetic demo identities
        </span>
      </div>

      <PageHeader
        eyebrow="Demo access"
        title="Sign in to EIR"
        description="Synthetic demo identities. Choose a role to explore the hospital."
        density="staff"
      />

      {error ? <ErrorAlert message={error} /> : null}

      {loading ? (
        <CardSkeleton rows={4} />
      ) : (
        <div className="grid gap-0 sm:grid-cols-3 sm:gap-7">
          {primary.map((user) => (
            <section
              key={user.username}
              className="flex flex-col border-t border-rule-strong pt-4"
            >
              <Avatar name={user.display_name} size="lg" />
              <span className="mt-4 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                {roleLabel(user.role)}
              </span>
              <h2 className="mt-1.5 text-[17px] font-medium text-ink">{user.display_name}</h2>
              <p className="mt-2 text-[13.5px] leading-[1.6] text-secondary">
                {user.copy?.description ?? "Explore this role."}
              </p>
              <Button
                className="mt-5 w-full"
                disabled={busy === user.username}
                onClick={() => void signIn(user.username, user.password_hint)}
              >
                {busy === user.username ? "Signing in…" : `Continue as ${user.display_name}`}
                <Icon name="arrowRight" size={16} />
              </Button>
            </section>
          ))}
        </div>
      )}

      {secondary.length ? (
        <div className="mt-10 flex flex-col">
          <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
            <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
              Alternate patient
            </h2>
          </div>
          {secondary.map((user) => (
            <div
              key={user.username}
              className="grid min-h-[60px] grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-rule py-3"
            >
              <span className="flex min-w-0 items-center gap-3">
                <Avatar name={user.display_name} size="sm" />
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="truncate text-[15px] text-ink">{user.display_name}</span>
                  <span className="truncate text-[13px] text-secondary">
                    {user.copy?.description}
                  </span>
                </span>
              </span>
              <Button
                variant="secondary"
                disabled={busy === user.username}
                onClick={() => void signIn(user.username, user.password_hint)}
              >
                {busy === user.username ? "Signing in…" : "Continue"}
                <Icon name="arrowRight" size={16} />
              </Button>
            </div>
          ))}
        </div>
      ) : null}

      <p className="mt-10 border-t border-rule pt-5 text-[13.5px] text-secondary">
        Prefer the guided story?{" "}
        <Link
          href="/demo"
          className="focus-ink font-medium text-accent hover:text-ink"
        >
          Open the live recovery demo
        </Link>
      </p>
    </section>
  );
}
