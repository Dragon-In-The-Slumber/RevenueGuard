"use client";
import { useApi } from "@/hooks/useApi";
import { Metrics } from "@/lib/types";

export default function KpiCards() {
  const { data: metrics } = useApi<Metrics>("/api/metrics");

  // Fallback defaults while loading
  const m = metrics || {
    totalAtRisk: 0,
    totalRecovered: 0,
    recoveryRate: 0,
    totalInvoices: 0,
    recoveredInvoices: 0
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
      {/* 1. Total At Risk */}
      <div className="glass-panel p-5 animate-fade-in" style={{ animationDelay: "0ms" }}>
        <p className="text-white/50 text-xs font-mono uppercase tracking-wider mb-2 flex items-center gap-2">
          <span className="text-amber-400">⚠️</span> Risk Exposure
        </p>
        <p className="text-2xl font-bold font-mono text-white">
          ₹{m.totalAtRisk.toLocaleString("en-IN")}
        </p>
      </div>

      {/* 2. Total Recovered */}
      <div className="glass-panel p-5 animate-fade-in" style={{ animationDelay: "100ms" }}>
        <p className="text-white/50 text-xs font-mono uppercase tracking-wider mb-2 flex items-center gap-2">
          <span className="text-emerald-400">💰</span> Total Recovered
        </p>
        <p className="text-2xl font-bold font-mono text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.5)]">
          ₹{m.totalRecovered.toLocaleString("en-IN")}
        </p>
      </div>

      {/* 3. Recovery Rate */}
      <div className="glass-panel p-5 animate-fade-in flex items-center justify-between" style={{ animationDelay: "200ms" }}>
        <div>
          <p className="text-white/50 text-xs font-mono uppercase tracking-wider mb-2 flex items-center gap-2">
            <span className="text-blue-400">📈</span> Win Rate
          </p>
          <p className="text-2xl font-bold font-mono text-white">
            {m.recoveryRate.toFixed(1)}%
          </p>
        </div>
        {/* Simple CSS gauge */}
        <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
            <path className="text-white/10" strokeWidth="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path className="text-[#00F0FF] transition-all duration-1000 ease-out" strokeDasharray={`${m.recoveryRate}, 100`} strokeWidth="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          </svg>
        </div>
      </div>

      {/* 4. Total Invoices */}
      <div className="glass-panel p-5 animate-fade-in" style={{ animationDelay: "300ms" }}>
        <p className="text-white/50 text-xs font-mono uppercase tracking-wider mb-2 flex items-center gap-2">
          <span className="text-cyan-400">📄</span> Total Invoices
        </p>
        <p className="text-2xl font-bold font-mono text-white">
          {m.totalInvoices}
        </p>
      </div>

      {/* 5. Recovered Invoices */}
      <div className="glass-panel p-5 animate-fade-in" style={{ animationDelay: "400ms" }}>
        <p className="text-white/50 text-xs font-mono uppercase tracking-wider mb-2 flex items-center gap-2">
          <span className="text-emerald-400">✅</span> Resolved
        </p>
        <p className="text-2xl font-bold font-mono text-white">
          {m.recoveredInvoices}
        </p>
      </div>
    </div>
  );
}
