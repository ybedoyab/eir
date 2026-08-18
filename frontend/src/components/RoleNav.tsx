"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { clearSession, loadSession, roleHome, type AuthSession, type DemoRole } from "@/lib/auth";

const NAV_BY_ROLE: Record<DemoRole, Array<{ href: string; label: string }>> = {
  PATIENT: [
    { href: "/patient", label: "Home" },
    { href: "/patient/appointments", label: "Appointments" },
    { href: "/patient/recovery", label: "Recovery" },
    { href: "/patient/assistant", label: "Ask EIR" },
  ],
  CLINICIAN: [
    { href: "/clinician", label: "Overview" },
    { href: "/clinician/reviews", label: "Reviews" },
    { href: "/clinician/patients", label: "Patients" },
  ],
  OPERATIONS_ADMIN: [
    { href: "/admin", label: "Command Center" },
    { href: "/admin/appointments", label: "Appointments" },
    { href: "/admin/patients", label: "Patients" },
    { href: "/admin/fleet", label: "Fleet" },
    { href: "/admin/observability", label: "Observability" },
  ],
};

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function RoleNav({ role }: { role: DemoRole }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    setSession(loadSession());
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href={roleHome(role)} className="group flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-700 text-sm font-semibold text-white shadow-sm">
            E
          </span>
          <span className="hidden sm:block">
            <span className="block text-sm font-semibold text-slate-900 group-hover:text-teal-800">
              EIR
            </span>
            <span className="block text-xs text-slate-500">Healthcare Agent Fleet</span>
          </span>
        </Link>

        <nav className="flex flex-wrap items-center gap-1" aria-label="Primary">
          {NAV_BY_ROLE[role].map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600",
                isActive(pathname, link.href)
                  ? "bg-teal-50 text-teal-800"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="hidden rounded-lg px-3 py-2 text-xs font-medium text-slate-500 hover:bg-slate-100 sm:inline-flex"
          >
            Switch demo role
          </Link>
          {session ? (
            <span className="hidden text-xs text-slate-500 sm:inline">{session.display_name}</span>
          ) : null}
          <Button
            variant="secondary"
            className="px-3 py-1.5 text-xs"
            onClick={() => {
              clearSession();
              router.push("/login");
            }}
          >
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
