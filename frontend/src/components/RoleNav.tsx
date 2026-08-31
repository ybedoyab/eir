"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { APP_META, APP_ROUTES } from "@/config/app";
import {
  isNavigationItemActive,
  ROLE_NAVIGATION,
  type NavigationItem,
  type RoleNavigation,
} from "@/config/navigation";
import { clearSession, loadSession, type AuthSession, type DemoRole } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { displayPatientId } from "@/lib/format";
import { roleLabel } from "@/lib/personas";

function Wordmark({ label }: { label: string }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className="eir-icon-shell h-10 w-10 rounded-xl">
        <Logo size={23} />
      </span>
      <span className="flex flex-col">
        <span className="font-serif text-[1.25rem] font-semibold leading-none tracking-[-0.01em] text-ink">
          {APP_META.name}
        </span>
        <span className="mt-1 font-mono text-[9.5px] uppercase tracking-[0.13em] text-muted">
          {label}
        </span>
      </span>
    </span>
  );
}

function NavItem({
  item,
  pathname,
  config,
  onNavigate,
}: {
  item: NavigationItem;
  pathname: string;
  config: RoleNavigation;
  onNavigate?: () => void;
}) {
  const active = isNavigationItemActive(pathname, item.href);

  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
      className={cn(
        "focus-ink group relative flex items-center gap-3 rounded-xl border",
        config.shell.navRow,
        config.shell.density,
        active
          ? "on-accent border-accent/70 bg-gradient-to-r from-accent to-accent-hover font-medium text-paper shadow-[0_10px_24px_rgb(22_75_130/0.2)]"
          : "border-transparent text-secondary hover:border-rule hover:bg-surface/80 hover:text-ink hover:shadow-[0_8px_22px_rgb(22_75_130/0.07)]",
      )}
    >
      <span
        className={cn(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          active ? "bg-white/14 text-paper" : "bg-accent-tint/60 text-accent",
        )}
      >
        <Icon name={item.icon} size={17} />
      </span>
      <span className="flex-1">{item.label}</span>
      <Icon
        name="chevronRight"
        size={14}
        className={cn(
          "opacity-0 group-hover:opacity-100",
          active ? "translate-x-0 text-paper opacity-100" : "-translate-x-1 text-muted",
        )}
      />
    </Link>
  );
}

function NavRows({
  config,
  pathname,
  onNavigate,
}: {
  config: RoleNavigation;
  pathname: string;
  onNavigate?: () => void;
}) {
  return config.navigation.map((item) => (
    <NavItem
      key={item.href}
      item={item}
      pathname={pathname}
      config={config}
      onNavigate={onNavigate}
    />
  ));
}

function IdentityPanel({
  role,
  session,
  onSignOut,
}: {
  role: DemoRole;
  session: AuthSession | null;
  onSignOut: () => void;
}) {
  const identityLabel = session?.patient_id
    ? displayPatientId(session.patient_id)
    : roleLabel(role).toLowerCase();

  return (
    <div className="eir-surface-soft flex flex-col gap-3 p-3.5">
      <div className="flex items-center gap-3">
        <span className="eir-status-dot" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[0.875rem] font-semibold text-ink">
            {session?.display_name ?? roleLabel(role)}
          </span>
          <span className="block truncate font-mono text-[0.6875rem] text-muted">
            {identityLabel}
          </span>
        </span>
      </div>
      <div className="grid grid-cols-2 gap-1 border-t border-rule/70 pt-2">
        <Link
          href={APP_ROUTES.login}
          onClick={clearSession}
          className="eir-control focus-ink inline-flex min-h-9 items-center justify-center gap-1.5 px-2 text-[0.75rem] text-secondary hover:bg-hover hover:text-ink"
        >
          <Icon name="swap" size={14} />
          Switch role
        </Link>
        <button
          type="button"
          onClick={onSignOut}
          className="eir-control focus-ink inline-flex min-h-9 items-center justify-center gap-1.5 px-2 text-[0.75rem] text-secondary hover:bg-hover hover:text-ink"
        >
          <Icon name="signOut" size={14} />
          Sign out
        </button>
      </div>
    </div>
  );
}

export function RoleNav({ role }: { role: DemoRole }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [open, setOpen] = useState(false);
  const config = ROLE_NAVIGATION[role];

  useEffect(() => setSession(loadSession()), []);
  useEffect(() => setOpen(false), [pathname]);

  function signOut() {
    clearSession();
    router.push(APP_ROUTES.login);
  }

  const identity = <IdentityPanel role={role} session={session} onSignOut={signOut} />;

  return (
    <>
      <header className="eir-glass sticky top-0 z-40 border-b border-rule/80 lg:hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <Link href={config.home} className="focus-ink inline-flex min-h-11 items-center rounded-xl">
            <Wordmark label={config.label} />
          </Link>
          <button
            type="button"
            className="focus-ink inline-flex h-11 w-11 items-center justify-center rounded-xl border border-rule bg-surface/70 text-body hover:bg-hover"
            aria-expanded={open}
            aria-controls="role-nav-mobile"
            onClick={() => setOpen((value) => !value)}
          >
            <Icon name={open ? "close" : "menu"} size={20} />
            <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          </button>
        </div>
        {open ? (
          <div id="role-nav-mobile" className="eir-enter border-t border-rule px-4 pb-4">
            <nav className="flex flex-col gap-1.5 py-3" aria-label="Primary">
              <NavRows config={config} pathname={pathname} onNavigate={() => setOpen(false)} />
            </nav>
            {identity}
          </div>
        ) : null}
      </header>

      <aside
        className={cn(
          "eir-glass sticky top-0 z-30 hidden h-screen flex-col gap-0.5 overflow-x-hidden overflow-y-auto border-r border-rule/80 lg:flex",
          config.shell.navPadding,
        )}
      >
        <span className="eir-orb eir-drift pointer-events-none absolute -right-10 -top-10 h-24 w-24 opacity-20" aria-hidden />
        <Link href={config.home} className="focus-ink relative mb-5 inline-flex min-h-11 items-center rounded-xl px-2">
          <Wordmark label={config.label} />
        </Link>
        <nav className="relative flex flex-col gap-1.5" aria-label="Primary">
          <NavRows config={config} pathname={pathname} />
        </nav>
        <div className="relative mt-auto pt-6">{identity}</div>
      </aside>
    </>
  );
}
