import type { ReactNode } from "react";

import { RoleNav } from "@/components/RoleNav";
import { ROLE_NAVIGATION } from "@/config/navigation";
import { cn } from "@/lib/cn";
import type { DemoRole } from "@/lib/auth";

export function PortalShell({ children, role }: { children: ReactNode; role: DemoRole }) {
  const shell = ROLE_NAVIGATION[role].shell;

  return (
    <div className={cn("eir-page min-h-screen lg:grid", shell.columns)}>
      <RoleNav role={role} />
      <main className={cn("eir-stagger flex min-w-0 w-full flex-col", shell.content)}>
        {children}
      </main>
    </div>
  );
}
