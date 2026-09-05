"use client";
import { useApi } from "@/hooks/useApi";
import QueryBoundary from "@/components/QueryBoundary";

interface RagContextResponse {
  context: string;
  profile: {
    tier: string;
    contact: string;
    risk_level: string;
    terms: string;
    history_summary: string;
  };
}

export default function RagContextPanel({ clientName }: { clientName: string }) {
  const { data, error, isLoading, mutate } = useApi<RagContextResponse>(
    `/api/clients/${encodeURIComponent(clientName)}/context`
  );

  if (error || isLoading || !data) {
    return (
      <div className="glass-panel p-5">
        <QueryBoundary
          error={error}
          loading={isLoading || !data}
          onRetry={() => mutate()}
          loadingFallback={
            <div className="animate-pulse">
              <div className="h-4 bg-white/10 rounded w-1/2 mb-4"></div>
              <div className="h-2 bg-white/10 rounded w-full mb-2"></div>
              <div className="h-2 bg-white/10 rounded w-3/4"></div>
            </div>
          }
        >
          {null}
        </QueryBoundary>
      </div>
    );
  }

  const { profile } = data;
  const isHighRisk = profile.risk_level === "HIGH" || profile.risk_level === "EXTREME";

  return (
    <div className="glass-panel p-5 relative overflow-hidden group">
      <div className="absolute -right-10 -top-10 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl group-hover:bg-purple-500/20 transition-colors" />
      
      <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-widest flex items-center gap-2">
        <span className="text-purple-400">🧠</span> Client Profile
      </h3>

      <div className="space-y-4">
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">Company Tier</p>
          <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-white/10 text-white/90">
            {profile.tier}
          </span>
        </div>

        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">Contact</p>
          <p className="text-sm text-white/80">{profile.contact}</p>
        </div>

        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">Contract Terms</p>
          <p className="text-sm text-white/80 font-mono text-[#00F0FF]">{profile.terms}</p>
        </div>

        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">Risk Level</p>
          <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
            isHighRisk ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
          }`}>
            {profile.risk_level} RISK
          </span>
        </div>

        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">History</p>
          <p className="text-xs text-white/60 leading-relaxed bg-black/20 p-2 rounded">
            {profile.history_summary}
          </p>
        </div>

        {isHighRisk && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded">
            <p className="text-[10px] uppercase font-mono tracking-wider text-red-400 mb-1 flex items-center gap-1">
              <span>⚠️</span> Strategic Guardrail
            </p>
            <p className="text-xs text-red-200/80">
              High risk client. Do not offer extensions. Proceed to STAGE_4 rapidly if unresponsive.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
