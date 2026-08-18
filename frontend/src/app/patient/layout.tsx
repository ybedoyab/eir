import type { ReactNode } from "react";

import { RoleNav } from "@/components/RoleNav";

export default function PatientLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <RoleNav role="PATIENT" />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
    </div>
  );
}
