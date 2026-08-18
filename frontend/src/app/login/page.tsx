"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { loadSession, roleHome, saveSession } from "@/lib/auth";
import { listDemoUsers, loginDemo } from "@/services/api";

export default function LoginPage() {
  const router = useRouter();
  const [users, setUsers] = useState<
    Array<{ username: string; display_name: string; role: string; password_hint: string }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    const existing = loadSession();
    if (existing) {
      router.replace(roleHome(existing.role));
    }
    void listDemoUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load demo users"));
  }, [router]);

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
    <section className="mx-auto max-w-3xl">
      <PageHeader
        eyebrow="Demo access"
        title="Sign in to EIR"
        description="Synthetic hackathon identities only. Choose a role to explore the hospital agent fleet."
      />
      {error ? <ErrorAlert message={error} /> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        {users.map((user) => (
          <Card key={user.username} className="flex h-full flex-col justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-teal-700">{user.role}</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-900">{user.display_name}</h2>
              <p className="mt-2 text-sm text-slate-600">Username: {user.username}</p>
              <p className="text-sm text-slate-500">Password: {user.password_hint}</p>
            </div>
            <Button
              className="mt-6 w-full"
              disabled={busy === user.username}
              onClick={() => void signIn(user.username, user.password_hint)}
            >
              Continue as {user.display_name}
            </Button>
          </Card>
        ))}
      </div>
      <p className="mt-8 text-center text-sm text-slate-500">
        Prefer the guided story?{" "}
        <Link href="/demo" className="font-medium text-teal-700 hover:text-teal-800">
          Open the live recovery demo
        </Link>
      </p>
    </section>
  );
}
