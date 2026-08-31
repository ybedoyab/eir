import Image from "next/image";

import { cn } from "@/lib/cn";

export function Logo({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("relative inline-flex shrink-0", className)}
      style={{ height: size, width: size }}
    >
      <Image src="/brand/logo-mark.png" alt="" fill sizes={`${size}px`} className="object-contain" priority />
    </span>
  );
}
