"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApi, ApiError } from "@/hooks/useApi";

const navItems = [
  { href: "/", label: "Command Center", icon: "📊" },
  { href: "/invoices", label: "Invoices", icon: "📋" },
  { href: "/graph", label: "AI Graph", icon: "🧠" },
  { href: "/clients", label: "Client Intel", icon: "👥" },
  { href: "/compliance", label: "Compliance", icon: "⚖️" },
  { href: "/approvals", label: "Approvals", icon: "🙋" },
  { href: "/events", label: "Events", icon: "🔔" },
];

export default function Sidebar() {
  const pathname = usePathname();
  
  // Try to ping health to see if backend is connected
  const { data: health, error } = useApi<{status: string}>("/health");
  const isConnected = !!health && !error;

  // Name the actual failure rather than calling every failure "offline".
  const statusLabel = isConnected
    ? "Backend Connected"
    : error instanceof ApiError
      ? `Backend error ${error.status}`
      : error
        ? "Backend unreachable"
        : "Connecting…";

  // Fetch virtual date
  const { data: simState, error: simError } = useApi<{virtual_date: string}>("/api/simulation/state");

  return (
    <aside className="sidebar flex flex-col h-full bg-[#0B0F19] border-r border-white/5 w-64">
      {/* Logo */}
      <div className="px-5 pt-6 pb-4 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" 
               style={{ background: "linear-gradient(135deg, #00F0FF, #8B5CF6)" }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
            </svg>
          </div>
          <div>
            <p className="text-white font-bold text-sm tracking-tight leading-tight">RevenueGuard</p>
            <p className="text-white/30 text-[10px] font-mono uppercase tracking-widest">AI Recovery</p>
          </div>
        </div>
      </div>

      {/* Virtual Date Display */}
      <div className="px-5 py-4 border-b border-white/5">
        <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-white/25 mb-1">Virtual Date</p>
        <div className="flex items-center gap-2">
          <span className="text-xl">⏱️</span>
          <span className={`font-mono text-sm ${simError ? "text-red-400" : "text-white/90"}`}>
            {simError
              ? `Unavailable (${simError instanceof ApiError ? simError.status : "no connection"})`
              : simState?.virtual_date
                ? new Date(simState.virtual_date).toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric'
                  })
                : "Waiting for tick..."}
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-white/25 px-3 mb-3">Navigation</p>
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href} className={`nav-item ${isActive ? "active" : ""}`}>
              <span className="nav-icon text-lg">{item.icon}</span>
              <span>{item.label}</span>
              {isActive && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[#00F0FF] shadow-[0_0_6px_#00F0FF]" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Backend Status at Bottom */}
      <div className="px-5 py-4 border-t border-white/5">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${
            isConnected
              ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
              : error
                ? 'bg-red-400 shadow-[0_0_8px_#f87171]'
                : 'bg-amber-400 shadow-[0_0_8px_#fbbf24]'
          }`} />
          <span className={`text-xs font-mono ${error ? 'text-red-400' : 'text-white/50'}`}>
            {statusLabel}
          </span>
        </div>
      </div>
    </aside>
  );
}
