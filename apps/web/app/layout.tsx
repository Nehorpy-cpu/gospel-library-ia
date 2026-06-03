import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { AppProviders } from "@/components/layout/app-providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"),
  title: {
    default: "Gospel Library IA",
    template: "%s | Gospel Library IA"
  },
  description:
    "Biblioteca doctrinal inteligente con busqueda IA, RAG, discursos, escrituras, PDFs, audio y citas verificables.",
  openGraph: {
    title: "Gospel Library IA",
    description: "Estudia doctrina con busqueda hibrida, chat IA y fuentes verificables.",
    type: "website"
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f766e"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={inter.className}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
