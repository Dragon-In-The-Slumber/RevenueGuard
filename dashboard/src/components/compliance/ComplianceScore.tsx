"use client";
import { useApi } from "@/hooks/useApi";
import QueryBoundary from "@/components/QueryBoundary";

interface ComplianceStats {
  total_checked: number;
  passed: number;
  failed: number;
  unreviewed: number;
  deterministic: number;
  /** null when nothing has been checked — an empty database is not a 100% record. */
  rate: number | null;
}

export default function ComplianceScore() {
  const { data, error, isLoading, mutate } = useApi<ComplianceStats>("/api/compliance/stats");

  if (error || isLoading || !data) {
    return (
      <div className="glass-panel p-6">
        <QueryBoundary
          error={error}
          loading={isLoading || !data}
          onRetry={() => mutate()}
          loadingFallback={<div className="h-48 animate-pulse rounded bg-white/5" />}
        >
          <div className="h-48" />
        </QueryBoundary>
      </div>
    );
  }

  const hasVerdicts = data.rate !== null && data.total_checked > 0;

  return (
    <div className="glass-panel p-8 flex flex-col items-center justify-center relative overflow-hidden group">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl opacity-50" />

      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest text-center w-full relative z-10">
        AI Compliance Rate
      </h3>

      <div className="relative w-48 h-48 flex items-center justify-center mb-6 z-10">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
          {hasVerdicts && (
            <circle
              cx="50" cy="50" r="45" fill="none"
              stroke={data.rate === 100 ? "#34d399" : "#fbbf24"}
              strokeWidth="10"
              strokeDasharray="283"
              strokeDashoffset={283 - (283 * (data.rate ?? 0)) / 100}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
            />
          )}
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center px-6">
          {hasVerdicts ? (
            <>
              <span className="text-4xl font-mono font-bold text-white tracking-tighter">
                {Math.round(data.rate ?? 0)}%
              </span>
              <span className="text-[10px] uppercase font-mono tracking-wider text-white/50 mt-1">
                Pass Rate
              </span>
            </>
          ) : (
            /* An empty record is not a perfect record. This used to render a
               green 100% ring before a single draft had been written. */
            <>
              <span className="text-2xl font-mono text-white/30">—</span>
              <span className="text-[10px] uppercase font-mono tracking-wider text-white/40 mt-2 leading-relaxed">
                No drafts checked yet
              </span>
            </>
          )}
        </div>
      </div>

      <div className="flex w-full justify-between px-2 relative z-10">
        <div className="text-center">
          <p className="text-2xl font-mono text-emerald-400 font-bold">{data.passed}</p>
          <p className="text-[10px] uppercase font-mono text-white/30 tracking-wider">Passed</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-mono text-red-400 font-bold">{data.failed}</p>
          <p className="text-[10px] uppercase font-mono text-white/30 tracking-wider">Failed</p>
        </div>
        <div className="text-center" title="Sent without review — the judge was unavailable">
          <p className="text-2xl font-mono text-amber-400 font-bold">{data.unreviewed}</p>
          <p className="text-[10px] uppercase font-mono text-white/30 tracking-wider">Unreviewed</p>
        </div>
      </div>

      {/* The rate is over genuine verdicts only. Say so, and say how many came
          from demo scaffolding rather than a model. */}
      <p className="mt-5 text-[10px] font-mono text-white/30 text-center leading-relaxed relative z-10">
        Rate over {data.total_checked} model verdict{data.total_checked === 1 ? "" : "s"}
        {data.unreviewed > 0 && ` · ${data.unreviewed} sent unreviewed`}
        {data.deterministic > 0 && (
          <>
            <br />
            {data.deterministic} verdict{data.deterministic === 1 ? "" : "s"} from deterministic
            scaffolding (DEMO_FAST), not a model
          </>
        )}
      </p>
    </div>
  );
}
