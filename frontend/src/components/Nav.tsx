"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { APP_META, APP_ROUTES } from "@/config/app";
import { isNavigationItemActive, PUBLIC_NAVIGATION } from "@/config/navigation";
import { cn } from "@/lib/cn";

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="eir-glass sticky top-0 z-40 border-b border-rule/80">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-2 sm:px-6">
        <Link href={APP_ROUTES.home} className="focus-ink group inline-flex min-h-11 items-center gap-2.5 rounded-xl">
          <span className="eir-icon-shell h-9 w-9 rounded-xl">
            <Logo size={20} />
          </span>
          <span className="font-serif text-[1.3125rem] font-semibold tracking-[-0.01em] text-ink">
            {APP_META.name}
          </span>
          <span className="h-4 w-px bg-rule-strong" aria-hidden />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            Recovery fleet
          </span>
        </Link>

        <nav className="flex flex-wrap items-center gap-1" aria-label="Primary">
          {PUBLIC_NAVIGATION.map((link) => {
            const active = isNavigationItemActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "focus-ink group inline-flex min-h-10 items-center gap-2 rounded-xl border px-3 text-sm",
                  active
                    ? "border-accent/20 bg-accent-tint font-medium text-accent shadow-[0_5px_14px_rgb(22_75_130/0.08)]"
                    : "border-transparent text-secondary hover:bg-surface/70 hover:text-ink",
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
