import type { ReactNode } from "react";

import { PortalShell } from "@/components/layout/PortalShell";

export default function PatientLayout({ children }: { children: ReactNode }) {
  return <PortalShell role="PATIENT">{children}</PortalShell>;
}
