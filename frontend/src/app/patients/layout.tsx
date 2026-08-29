import type { ReactNode } from "react";

/**
 * `/patients` and `/patients/[id]` sit outside every role portal, so nothing
 * upstream supplies the page gutters — without this the section rendered flush
 * against both viewport edges while `app/loading.tsx` painted its skeleton
 * inside a padded container. Same frame as that boundary.
 */
export default function PatientsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-paper">
      <main className="mx-auto flex max-w-6xl flex-col px-5 py-10 sm:px-8">{children}</main>
    </div>
  );
}
