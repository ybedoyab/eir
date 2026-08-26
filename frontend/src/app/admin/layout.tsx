import type { ReactNode } from "react";

import { RoleNav } from "@/components/RoleNav";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-paper lg:grid lg:grid-cols-[210px_minmax(0,1fr)]">
      <RoleNav role="OPERATIONS_ADMIN" />
      <main className="flex min-w-0 flex-col gap-6 px-5 py-6 sm:px-7">{children}</main>
    </div>
  );
}
