import type { ReactNode } from "react";

export default function PatientsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="eir-page min-h-screen">
      <main className="mx-auto flex max-w-6xl flex-col px-5 py-10 sm:px-8">{children}</main>
    </div>
  );
}
