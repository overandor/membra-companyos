import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MEMBRA CompanyOS",
  description: "AI-powered autonomous company orchestration layer.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-membrabg text-white antialiased">{children}</body>
    </html>
  );
}
