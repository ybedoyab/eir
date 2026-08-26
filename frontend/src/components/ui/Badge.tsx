import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** A square mono chip. Neutral unless the caller is communicating state. */
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
        "inline-flex h-[26px] w-fit items-center px-2.5 font-mono text-[11.5px] uppercase leading-none tracking-[0.06em] text-secondary",
        className,
      )}
    >
      {children}
    </span>
  );
}
