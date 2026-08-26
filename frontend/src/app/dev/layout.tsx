import type { ReactNode } from "react";

import Link from "next/link";

import { Icon } from "@/components/ui/Icon";

export default function DevLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-paper">
      <header className="on-raised border-b border-rule bg-raised">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
          <Link href="/" className="focus-ink inline-flex min-h-11 items-center gap-3">
            <span className="font-serif text-[19px] font-semibold tracking-[-0.01em] text-ink">
              EIR
            </span>
            <span className="h-4 w-px bg-rule-strong" aria-hidden />
            <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
              Developer
            </span>
          </Link>
          <Link
            href="/login"
            className="focus-ink inline-flex min-h-11 items-center gap-2 text-sm text-accent hover:text-ink"
          >
            <Icon name="arrowLeft" size={15} />
            Back to portal
          </Link>
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-7 px-5 py-8 sm:px-8 sm:py-10">
        {children}
      </main>
    </div>
  );
}
