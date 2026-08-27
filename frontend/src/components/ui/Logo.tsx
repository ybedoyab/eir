import Image from "next/image";

import { cn } from "@/lib/cn";

/**
 * The EIR hourglass-and-capsules mark. Source lives at public/brand/logo-mark.png
 * (background removed from the project logo); this is the one place its aspect
 * ratio and rendering are pinned so every wordmark stays visually consistent.
 */
export function Logo({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <Image
      src="/brand/logo-mark.png"
      alt=""
      width={size}
      height={size}
      className={cn("shrink-0 object-contain", className)}
      style={{ height: size, width: "auto" }}
      priority
    />
  );
}
