"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon, type IconName } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { cn } from "@/lib/cn";
import { clearSession, loadSession, roleHome, type AuthSession, type DemoRole } from "@/lib/auth";
import { roleLabel } from "@/lib/personas";

interface NavLink {
  href: string;
  label: string;
  icon: IconName;
}

const NAV_BY_ROLE: Record<DemoRole, NavLink[]> = {
  PATIENT: [
    { href: "/patient", label: "Home", icon: "home" },
    { href: "/patient/appointments", label: "Appointments", icon: "schedule" },
    { href: "/patient/recovery", label: "Recovery", icon: "recovery" },
    { href: "/patient/assistant", label: "Ask EIR", icon: "assistant" },
  ],
  CLINICIAN: [
    { href: "/clinician", label: "Today", icon: "today" },
    { href: "/clinician/schedule", label: "Schedule", icon: "schedule" },
    { href: "/clinician/reviews", label: "Reviews", icon: "reviews" },
    { href: "/clinician/patients", label: "Patients", icon: "patients" },
  ],
  OPERATIONS_ADMIN: [
    { href: "/admin", label: "Overview", icon: "overview" },
    { href: "/admin/fleet", label: "Fleet", icon: "fleet" },
    { href: "/admin/observability", label: "Observability", icon: "observe" },
    { href: "/admin/appointments", label: "Appointments", icon: "schedule" },
    { href: "/admin/patients", label: "Patients", icon: "patients" },
    { href: "/admin/inventory", label: "Inventory", icon: "inventory" },
  ],
};

/** Density is the same dials at three settings; targets never shrink. */
const RAIL: Record<DemoRole, { pad: string; row: string; text: string; kicker: string }> = {
  PATIENT: { pad: "px-5 py-6", row: "min-h-12 px-3", text: "text-[0.9375rem]", kicker: "Patient" },
  CLINICIAN: {
    pad: "px-4 py-5",
    row: "min-h-11 px-2.5",
    text: "text-[14.5px]",
    kicker: "Clinician",
  },
  OPERATIONS_ADMIN: {
    pad: "px-3.5 py-4.5",
    row: "min-h-11 px-2.5",
    text: "text-[0.875rem]",
    kicker: "Operations",
  },
};

function isActive(pathname: string, href: string): boolean {
  if (href === "/patient" || href === "/clinician" || href === "/admin") {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Wordmark({ kicker, size, logoSize = 20 }: { kicker: string; size: string; logoSize?: number }) {
  return (
    <span className="flex items-center gap-2.5">
      <Logo size={logoSize} />
      <span className={cn("font-serif font-semibold tracking-[-0.01em] text-ink", size)}>EIR</span>
      <span className="h-4 w-px bg-rule-strong" aria-hidden />
      <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
        {kicker}
      </span>
    </span>
  );
}

function NavRows({
  links,
  pathname,
  density,
  onNavigate,
}: {
  links: NavLink[];
  pathname: string;
  density: (typeof RAIL)[DemoRole];
  onNavigate?: () => void;
}) {
  return (
    <>
      {links.map((link) => {
        const active = isActive(pathname, link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            onClick={onNavigate}
            className={cn(
              "focus-ink group flex items-center gap-3 border-l-[3px]",
              density.row,
              density.text,
              active
                ? "border-accent bg-paper font-medium text-ink"
                : "border-transparent text-secondary hover:bg-hover hover:text-ink",
            )}
          >
            <Icon name={link.icon} size={18} className={active ? "text-accent" : undefined} />
            <span className="flex-1">{link.label}</span>
            <Icon
              name="chevronRight"
              size={14}
              className={cn(
                "text-muted opacity-0 group-hover:opacity-100",
                active && "opacity-100 text-accent",
              )}
            />
          </Link>
        );
      })}
    </>
  );
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
  const density = RAIL[role];

  function signOut() {
    clearSession();
    router.push("/login");
  }

  const identity = (
    <div className="flex flex-col gap-2 border-t border-rule pt-4">
      <div className="flex flex-col gap-0.5">
        <span className="text-[0.875rem] font-medium text-ink">
          {session?.display_name ?? roleLabel(role)}
        </span>
        <span className="font-mono text-[0.75rem] text-muted">
          {session?.patient_id ?? roleLabel(role).toLowerCase()}
        </span>
      </div>
      <span className="font-mono text-[10.5px] leading-snug text-muted">
        Synthetic demo identity
      </span>
      <div className="mt-1 flex flex-wrap items-center gap-1">
        <Link
          href="/login"
          onClick={() => clearSession()}
          className="focus-ink inline-flex min-h-11 items-center px-2 text-[0.8125rem] text-secondary hover:text-ink"
        >
          Switch role
        </Link>
        <button
          type="button"
          onClick={signOut}
          className="focus-ink inline-flex min-h-11 items-center gap-2 px-2 text-[0.8125rem] text-secondary hover:text-ink"
        >
          <Icon name="signOut" size={15} />
          Sign out
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile: a top bar that opens the same rows. */}
      <header className="on-raised sticky top-0 z-40 border-b border-rule bg-raised lg:hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <Link href={roleHome(role)} className="focus-ink inline-flex min-h-11 items-center">
            <Wordmark kicker={density.kicker} size="text-[1.1875rem]" logoSize={19} />
          </Link>
          <button
            type="button"
            className="focus-ink inline-flex h-11 w-11 items-center justify-center text-body hover:bg-hover"
            aria-expanded={open}
            aria-controls="role-nav-mobile"
            onClick={() => setOpen((value) => !value)}
          >
            <Icon name={open ? "close" : "menu"} size={20} />
            <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          </button>
        </div>
        {open ? (
          <div id="role-nav-mobile" className="border-t border-rule px-4 pb-4">
            <nav className="flex flex-col py-2" aria-label="Primary">
              <NavRows
                links={links}
                pathname={pathname}
                density={density}
                onNavigate={() => setOpen(false)}
              />
            </nav>
            {identity}
          </div>
        ) : null}
      </header>

      {/* Desktop: the rail. */}
      <aside
        className={cn(
          "on-raised sticky top-0 hidden h-screen flex-col gap-0.5 overflow-y-auto border-r border-rule bg-raised lg:flex",
          density.pad,
        )}
      >
        <Link
          href={roleHome(role)}
          className="focus-ink mb-4 inline-flex min-h-11 items-center px-3"
        >
          <Wordmark kicker={density.kicker} size="text-[1.3125rem]" logoSize={22} />
        </Link>
        <nav className="flex flex-col gap-0.5" aria-label="Primary">
          <NavRows links={links} pathname={pathname} density={density} />
        </nav>
        <div className="mt-auto pt-6">{identity}</div>
      </aside>
    </>
  );
}
