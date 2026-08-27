import type { ReactNode } from "react";

import { RoleNav } from "@/components/RoleNav";

export default function PatientLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-paper lg:grid lg:grid-cols-[260px_minmax(0,1fr)]">
      <RoleNav role="PATIENT" />
      {/* gap-14 separates top-level sections; blocks *inside* a section sit at
          gap-8, so the spacing itself carries the nesting. */}
      <main className="flex flex-col gap-14 px-5 py-10 sm:px-10 sm:py-12 lg:max-w-[1060px] lg:px-14">
        {children}
      </main>
    </div>
  );
}
