import type { ReactNode } from "react";

export default function ObservabilityLayout({ children }: { children: ReactNode }) {
  return (
    <div className="eir-page flex min-h-screen flex-col gap-6 px-5 py-6 sm:px-7">{children}</div>
  );
}
