"use client";

import {
  Activity,
  Bot,
  Building2,
  CalendarDays,
  ClipboardCheck,
  HeartPulse,
  Home,
  LogOut,
  Menu,
  MessageCircle,
  Package,
  Users,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { clearSession, loadSession, roleHome, type AuthSession, type DemoRole } from "@/lib/auth";
import { roleLabel } from "@/lib/personas";

const NAV_BY_ROLE: Record<DemoRole, Array<{ href: string; label: string; icon: LucideIcon }>> = {
  PATIENT: [
    { href: "/patient", label: "Home", icon: Home },
    { href: "/patient/appointments", label: "Appointments", icon: CalendarDays },
    { href: "/patient/recovery", label: "Recovery", icon: HeartPulse },
    { href: "/patient/assistant", label: "Ask EIR", icon: MessageCircle },
  ],
  CLINICIAN: [
    { href: "/clinician", label: "Overview", icon: Activity },
    { href: "/clinician/schedule", label: "Schedule", icon: CalendarDays },
    { href: "/clinician/reviews", label: "Reviews", icon: ClipboardCheck },
    { href: "/clinician/patients", label: "Patients", icon: Users },
  ],
  OPERATIONS_ADMIN: [
    { href: "/admin", label: "Command Center", icon: Building2 },
    { href: "/admin/appointments", label: "Appointments", icon: CalendarDays },
    { href: "/admin/patients", label: "Patients", icon: Users },
    { href: "/admin/inventory", label: "Inventory", icon: Package },
    { href: "/admin/fleet", label: "Fleet", icon: Bot },
    { href: "/admin/observability", label: "Observability", icon: Activity },
  ],
};

function isActive(pathname: string, href: string): boolean {
  if (href === "/patient" || href === "/clinician" || href === "/admin") {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function RoleNav({ role }: { role: DemoRole }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setSession(loadSession());
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const links = NAV_BY_ROLE[role];

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
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

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600",
                  isActive(pathname, link.href)
                    ? "bg-teal-50 text-teal-800"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                )}
              >
                <Icon aria-hidden className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          {session ? (
            <div className="hidden items-center gap-2 sm:flex">
              <Avatar name={session.display_name} size="sm" />
              <span className="hidden text-left md:block">
                <span className="block text-xs font-medium text-slate-800">{session.display_name}</span>
                <span className="block text-[11px] text-slate-500">
                  {roleLabel(session.role)} · Synthetic demo
                </span>
              </span>
            </div>
          ) : null}
          <Link
            href="/login"
            className="hidden rounded-lg px-3 py-2 text-xs font-medium text-slate-500 hover:bg-slate-100 lg:inline-flex"
            onClick={() => clearSession()}
          >
            Switch demo role
          </Link>
          <Button
            variant="ghost"
            className="hidden px-3 text-xs lg:inline-flex"
            onClick={() => {
              clearSession();
              router.push("/login");
            }}
          >
            <LogOut aria-hidden className="h-4 w-4" />
            Sign out
          </Button>
          <button
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 lg:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X aria-hidden className="h-5 w-5" /> : <Menu aria-hidden className="h-5 w-5" />}
            <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          </button>
        </div>
      </div>

      {open ? (
        <div id="mobile-nav" className="border-t border-slate-200 bg-white px-4 py-3 lg:hidden">
          <nav className="grid gap-1" aria-label="Mobile">
            {links.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "inline-flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium",
                    isActive(pathname, link.href)
                      ? "bg-teal-50 text-teal-800"
                      : "text-slate-700 hover:bg-slate-50",
                  )}
                >
                  <Icon aria-hidden className="h-4 w-4" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
            <Link href="/login" className="text-sm font-medium text-slate-500" onClick={() => clearSession()}>
              Switch demo role
            </Link>
            <Button
              variant="secondary"
              className="px-3 text-xs"
              onClick={() => {
                clearSession();
                router.push("/login");
              }}
            >
              Sign out
            </Button>
          </div>
          <p className="mt-3 text-center text-[11px] uppercase tracking-wide text-slate-400">
            Synthetic demo
          </p>
        </div>
      ) : null}
    </header>
  );
}
