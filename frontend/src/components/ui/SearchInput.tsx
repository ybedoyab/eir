"use client";

import type { InputHTMLAttributes } from "react";

import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

export function SearchInput({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={cn("group relative block", className)}>
      <span className="sr-only">{props["aria-label"] ?? props.placeholder ?? "Search"}</span>
      <Icon
        name="search"
        size={16}
        className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted group-focus-within:text-accent"
      />
      <input
        type="search"
        className="eir-control focus-ink h-11 w-full border border-rule bg-surface/80 py-2 pl-10 pr-3.5 text-sm text-ink shadow-[0_5px_18px_rgb(22_75_130/0.05)] placeholder:text-muted hover:border-rule-strong focus:border-accent focus:bg-surface"
        {...props}
      />
    </label>
  );
}
