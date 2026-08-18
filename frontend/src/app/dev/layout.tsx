import type { ReactNode } from "react";

import Link from "next/link";

export default function DevLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link href="/" className="text-sm font-semibold text-slate-900">
            EIR Developer
          </Link>
          <Link href="/login" className="text-sm text-teal-700">
            Back to portal
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
    </div>
  );
}
