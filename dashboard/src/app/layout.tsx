import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import { ToastProvider } from "@/components/ToastProvider";
import { WebSocketProvider } from "@/components/WebSocketProvider";
import Sidebar from "@/components/Sidebar";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "RevenueGuard | AI Command Center",
  description: "Autonomous AI-powered revenue recovery for failed payments — built for the Razorpay AI Buildathon.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${outfit.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">
        <ToastProvider>
          {/* One socket for the whole app, so every page updates live rather
              than only /graph. */}
          <WebSocketProvider>
            <div className="app-shell">
              <Sidebar />
              <div className="page-content">
                {children}
              </div>
            </div>
          </WebSocketProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
