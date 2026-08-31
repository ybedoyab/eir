import type { ReactNode } from "react";

import { PortalShell } from "@/components/layout/PortalShell";

export default function ClinicianLayout({ children }: { children: ReactNode }) {
  return <PortalShell role="CLINICIAN">{children}</PortalShell>;
}
