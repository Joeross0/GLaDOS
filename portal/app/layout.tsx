import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GLaDOS Portal",
  description: "Remote access to a local GLaDOS core",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
