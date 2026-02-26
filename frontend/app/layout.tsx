import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "STO — Social Trend Observant",
  description: "Friendly, AI-powered sentiment and risk-free trading practice for everyday investors",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <AuthProvider>
          <Header />
          <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
            {children}
          </main>
          <footer className="border-t border-sto-cardBorder bg-sto-card py-5 text-center text-sto-muted text-sm">
            <p><strong className="text-sto-text">STO</strong> — Social Trend Observant. For learning only; not financial advice.</p>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
