import type { ReactNode } from "react";

export default function RecoveryLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
    </div>
  );
}
