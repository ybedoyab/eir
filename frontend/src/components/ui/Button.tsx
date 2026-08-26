import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "destructive";

const variants: Record<Variant, string> = {
  primary: "bg-accent text-paper hover:bg-accent-hover",
  secondary: "border border-rule-strong text-body hover:bg-hover",
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
        "focus-ink inline-flex min-h-11 items-center justify-center gap-2.5 px-5 text-sm font-medium disabled:cursor-not-allowed disabled:bg-hover disabled:text-muted",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
