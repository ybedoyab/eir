import type { ReactNode } from "react";

import { RoleNav } from "@/components/RoleNav";

export default function ClinicianLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-paper lg:grid lg:grid-cols-[232px_minmax(0,1fr)]">
      <RoleNav role="CLINICIAN" />
      <main className="flex min-w-0 flex-col gap-7 px-5 py-7 sm:px-8">{children}</main>
    </div>
  );
}
