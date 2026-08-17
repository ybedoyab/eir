import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ApiStatus } from "@/components/ApiStatus";
import { Nav } from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "EIR — Enterprise Intelligence for Recovery",
  description: "A secure autonomous recovery fleet for healthcare.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <ApiStatus />
        <main style={{ padding: "1.5rem" }}>{children}</main>
      </body>
    </html>
  );
}
