import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive";

const variants: Record<ButtonVariant, string> = {
  primary:
    "on-accent bg-gradient-to-br from-accent-bright to-accent text-paper shadow-[0_10px_24px_rgb(22_75_130/0.2)] hover:-translate-y-0.5 hover:shadow-[0_14px_30px_rgb(22_75_130/0.28)]",
  secondary:
    "border border-accent/30 bg-surface/70 text-accent shadow-[0_4px_14px_rgb(22_75_130/0.06)] hover:-translate-y-0.5 hover:border-accent/60 hover:bg-accent-tint",
  ghost: "text-secondary hover:bg-hover/80 hover:text-ink",
  destructive:
    "bg-gradient-to-br from-high to-crit text-paper shadow-[0_10px_24px_rgb(178_58_34/0.18)] hover:-translate-y-0.5",
};

export function buttonStyles(variant: ButtonVariant = "primary", className?: string): string {
  return cn(
    "eir-control focus-ink group inline-flex min-h-11 items-center justify-center gap-2.5 px-5 text-sm font-semibold disabled:cursor-not-allowed disabled:border-rule-strong disabled:bg-hover disabled:text-muted disabled:shadow-none",
    variants[variant],
    className,
  );
}

export function Button({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: ButtonVariant;
}) {
  return (
    <button
      type="button"
      className={buttonStyles(variant, className)}
      {...props}
    >
      {children}
    </button>
  );
}
