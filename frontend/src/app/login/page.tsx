"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
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
      <div className="mb-8 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-700 text-sm font-semibold text-white">
          E
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-900">EIR</p>
          <p className="text-xs text-slate-500">Synthetic demo identities</p>
        </div>
      </div>
      <PageHeader
        eyebrow="Demo access"
        title="Sign in to EIR"
        description="Synthetic demo identities. Choose a role to explore the hospital."
      />
      {error ? <ErrorAlert message={error} /> : null}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          {primary.map((user) => (
            <Card key={user.username} className="flex h-full flex-col justify-between">
              <div>
                <Avatar name={user.display_name} size="lg" />
                <p className="mt-4 text-xs font-medium uppercase tracking-wide text-teal-700">
                  {roleLabel(user.role)}
                </p>
                <h2 className="mt-1 text-lg font-semibold text-slate-900">{user.display_name}</h2>
                <p className="mt-2 text-sm text-slate-600">
                  {user.copy?.description ?? "Explore this role."}
                </p>
              </div>
              <Button
                className="mt-6 w-full"
                disabled={busy === user.username}
                onClick={() => void signIn(user.username, user.password_hint)}
              >
                {busy === user.username ? "Signing in…" : `Continue as ${user.display_name}`}
              </Button>
            </Card>
          ))}
        </div>
      )}
      {secondary.length ? (
        <div className="mt-8">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-400">
            Alternate patient
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {secondary.map((user) => (
              <Card key={user.username} className="flex items-center justify-between gap-4 py-4">
                <div className="flex items-center gap-3">
                  <Avatar name={user.display_name} size="sm" />
                  <div>
                    <p className="font-medium text-slate-900">{user.display_name}</p>
                    <p className="text-sm text-slate-500">{user.copy?.description}</p>
                  </div>
                </div>
                <Button
                  variant="secondary"
                  disabled={busy === user.username}
                  onClick={() => void signIn(user.username, user.password_hint)}
                >
                  Continue
                </Button>
              </Card>
            ))}
          </div>
        </div>
      ) : null}
      <p className="mt-8 text-center text-sm text-slate-500">
        Prefer the guided story?{" "}
        <Link href="/demo" className="font-medium text-teal-700 hover:text-teal-800">
          Open the live recovery demo
        </Link>
      </p>
    </section>
  );
}
