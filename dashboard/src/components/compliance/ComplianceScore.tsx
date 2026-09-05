"use client";
import { useApi } from "@/hooks/useApi";
import QueryBoundary from "@/components/QueryBoundary";

export default function ComplianceScore() {
  const { data, error, isLoading, mutate } = useApi<{ total_checked: number, passed: number, failed: number, rate: number }>("/api/compliance/stats");

  if (error || isLoading || !data) {
    return (
      <div className="glass-panel p-6">
        <QueryBoundary
          error={error}
          loading={isLoading || !data}
          onRetry={() => mutate()}
          loadingFallback={<div className="h-48 animate-pulse rounded bg-white/5" />}
        >
          {null}
        </QueryBoundary>
      </div>
    );
  }

  return (
    <div className="glass-panel p-8 flex flex-col items-center justify-center relative overflow-hidden group">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl opacity-50" />
      
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest text-center w-full relative z-10">
        AI Compliance Rate
      </h3>
      
      <div className="relative w-48 h-48 flex items-center justify-center mb-6 z-10">
        {/* SVG Circle Gauge */}
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle 
            cx="50" cy="50" r="45" 
            fill="none" 
            stroke="rgba(255,255,255,0.05)" 
            strokeWidth="10" 
          />
          <circle 
            cx="50" cy="50" r="45" 
            fill="none" 
            stroke={data.rate === 100 ? "#34d399" : "#fbbf24"} 
            strokeWidth="10" 
            strokeDasharray="283"
            strokeDashoffset={283 - (283 * data.rate) / 100}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="text-4xl font-mono font-bold text-white tracking-tighter">
            {Math.round(data.rate)}%
          </span>
          <span className="text-[10px] uppercase font-mono tracking-wider text-white/50 mt-1">
            Pass Rate
          </span>
        </div>
      </div>
      
      <div className="flex w-full justify-between px-4 relative z-10">
        <div className="text-center">
          <p className="text-2xl font-mono text-emerald-400 font-bold">{data.passed}</p>
          <p className="text-[10px] uppercase font-mono text-white/30 tracking-wider">Passed</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-mono text-white font-bold">{data.total_checked}</p>
          <p className="text-[10px] uppercase font-mono text-white/30 tracking-wider">Checked</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-mono text-red-400 font-bold">{data.failed}</p>
          <p className="text-[10px] uppercase font-mono text-white/30 tracking-wider">Failed</p>
        </div>
      </div>
    </div>
  );
}
