"use client";

import type { InputHTMLAttributes } from "react";

import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

export function SearchInput({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={cn("relative block", className)}>
      <span className="sr-only">{props["aria-label"] ?? props.placeholder ?? "Search"}</span>
      <Icon
        name="search"
        size={16}
        className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted"
      />
      <input
        type="search"
        className="focus-ink h-11 w-full border border-rule-strong bg-paper py-2 pl-10 pr-3.5 text-sm text-ink placeholder:text-muted focus:border-accent"
        {...props}
      />
    </label>
  );
}
