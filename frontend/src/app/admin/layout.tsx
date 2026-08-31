import type { ReactNode } from "react";

import { PortalShell } from "@/components/layout/PortalShell";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <PortalShell role="OPERATIONS_ADMIN">{children}</PortalShell>;
}
