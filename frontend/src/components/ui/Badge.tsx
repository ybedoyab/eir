import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Badge({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "eir-chip inline-flex h-[26px] w-fit items-center border border-rule bg-surface/70 px-2.5 font-mono text-[11.5px] uppercase leading-none tracking-[0.06em] text-secondary",
        className,
      )}
    >
      {children}
    </span>
  );
}
