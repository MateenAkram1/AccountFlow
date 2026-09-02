import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AccountFlow OS",
  description: "Meeting-to-action with scope verification",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
