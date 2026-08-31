import type { ReactNode } from "react";

export default function RecoveryLayout({ children }: { children: ReactNode }) {
  return (
    <div className="eir-page min-h-screen">
      <main className="mx-auto flex max-w-6xl flex-col gap-7 px-5 py-8 sm:px-8 sm:py-10">
        {children}
      </main>
    </div>
  );
}
