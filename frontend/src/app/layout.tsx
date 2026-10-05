import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Toast } from "@/components/notifications/Toast";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "NeerNiti | AI Recharge Dashboard",
  description: "Cloud-native, AI-driven decision support system for groundwater management and recharge structure recommendation",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <body className="bg-slate-950 text-slate-100 font-sans antialiased overflow-x-hidden min-h-screen selection:bg-blue-600 selection:text-white">
        <Providers>
          {children}
          <Toast />
        </Providers>
      </body>
    </html>
  );
}
