import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "destructive";

/**
 * The hierarchy is one accent at three strengths, so a button's weight reads
 * before its label does: filled accent, outlined accent, then bare. Only
 * destructive leaves the accent, because it is a different kind of answer.
 */
const variants: Record<Variant, string> = {
  primary: "on-accent bg-accent text-paper hover:bg-accent-hover",
  secondary: "border border-accent text-accent hover:bg-accent-tint",
  ghost: "text-secondary hover:bg-hover hover:text-ink",
  destructive: "bg-high text-paper hover:bg-crit",
};

export function Button({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: Variant;
}) {
  return (
    <button
      type="button"
      className={cn(
        // Disabled drops the accent entirely — an outlined secondary would
        // otherwise keep its accent border and still read as live.
        "focus-ink inline-flex min-h-11 items-center justify-center gap-2.5 px-5 text-sm font-medium disabled:cursor-not-allowed disabled:border-rule-strong disabled:bg-hover disabled:text-muted",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
