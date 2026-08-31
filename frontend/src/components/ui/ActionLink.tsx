import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

import { buttonStyles, type ButtonVariant } from "@/components/ui/Button";

export function ActionLink({
  children,
  className,
  variant = "primary",
  ...props
}: ComponentProps<typeof Link> & {
  children: ReactNode;
  variant?: ButtonVariant;
}) {
  return (
    <Link className={buttonStyles(variant, className)} {...props}>
      {children}
    </Link>
  );
}
