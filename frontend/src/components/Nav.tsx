"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, type IconName } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

const links: Array<{ href: string; label: string; icon: IconName }> = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/demo", label: "Demo", icon: "fleet" },
  { href: "/patients", label: "Patients", icon: "patients" },
  { href: "/recovery", label: "Recovery", icon: "recovery" },
  { href: "/agents", label: "Agents", icon: "overview" },
  { href: "/observability", label: "Observability", icon: "observe" },
  { href: "/voice-preview", label: "Voice", icon: "voice" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="on-raised sticky top-0 z-40 border-b border-rule bg-raised">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="focus-ink inline-flex min-h-11 items-center gap-3">
          <span className="font-serif text-[1.3125rem] font-semibold tracking-[-0.01em] text-ink">
            EIR
          </span>
          <span className="h-4 w-px bg-rule-strong" aria-hidden />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            Recovery fleet
          </span>
        </Link>

        <nav className="flex flex-wrap items-center" aria-label="Primary">
          {links.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "focus-ink inline-flex min-h-11 items-center gap-2 border-b-[3px] px-3 text-sm",
                  active
                    ? "border-accent font-medium text-ink"
                    : "border-transparent text-secondary hover:text-ink",
                )}
              >
                <Icon name={link.icon} size={16} className={active ? "text-accent" : undefined} />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
