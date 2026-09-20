import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GLaDOS",
  description: "Local-style GLaDOS chat through Vercel, backed by your RunPod serve.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
