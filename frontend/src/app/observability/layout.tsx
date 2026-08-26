import type { ReactNode } from "react";

export default function ObservabilityLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col gap-6 bg-paper px-5 py-6 sm:px-7">{children}</div>
  );
}
