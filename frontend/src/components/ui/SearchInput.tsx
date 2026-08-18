"use client";

import { Search } from "lucide-react";
import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export function SearchInput({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={cn("relative block", className)}>
      <span className="sr-only">{props["aria-label"] ?? props.placeholder ?? "Search"}</span>
      <Search
        aria-hidden
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
      />
      <input
        type="search"
        className="h-11 w-full rounded-xl border border-slate-200 bg-white py-2 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-100"
        {...props}
      />
    </label>
  );
}
