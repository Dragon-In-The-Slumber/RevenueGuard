"use client";
import { useApi } from "@/hooks/useApi";
import { FunnelEntry } from "@/lib/types";
import { STATUS_CONFIG } from "@/lib/constants";
import StatusBadge from "@/components/invoices/StatusBadge";
import QueryBoundary from "@/components/QueryBoundary";

export default function RecoveryFunnel() {
  const { data: funnel, error, isLoading, mutate } = useApi<{ funnel: FunnelEntry[] }>("/api/funnel");
  
  const entries = funnel?.funnel || [];
  const maxCount = Math.max(...entries.map(e => e.count), 1); // Avoid division by zero

  return (
    <div className="glass-panel p-5 h-full flex flex-col">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-accent-primary">▼</span> Recovery Funnel
      </h3>
      
      <QueryBoundary
        error={error}
        loading={isLoading}
        isEmpty={entries.length === 0}
        emptyMessage="No active invoices. Generate a batch."
        onRetry={() => mutate()}
      >
        <div className="flex-1 space-y-4">
          {entries.map((entry) => {
            const config = STATUS_CONFIG[entry.status] || STATUS_CONFIG["ISSUED"];
            const percentage = (entry.count / maxCount) * 100;
            
            return (
              <div key={entry.status} className="relative">
                <div className="flex justify-between text-xs font-mono mb-1.5 z-10 relative">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={entry.status} />
                    <span className="text-white/70">{entry.count} invoices</span>
                  </div>
                  <span className="text-white/50">₹{entry.amount.toLocaleString("en-IN")}</span>
                </div>
                {/* Progress bar background */}
                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-1000 ease-out opacity-80"
                    style={{ 
                      width: `${percentage}%`,
                      backgroundColor: config.hex
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </QueryBoundary>
    </div>
  );
}
