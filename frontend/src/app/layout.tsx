import { Inter } from "next/font/google";
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/AppProviders";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "EIR — Healthcare Agent Fleet",
  description: "AI-powered hospital operations with secure multi-agent workflows.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
