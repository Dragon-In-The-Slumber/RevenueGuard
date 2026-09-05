"use client";
import { useApi } from "@/hooks/useApi";
import { AuditLogEntry } from "@/lib/types";
import { EVENT_TYPE_CONFIG } from "@/lib/constants";
import QueryBoundary from "@/components/QueryBoundary";
import { useVirtualDate } from "@/hooks/useVirtualDate";
import Link from "next/link";

export default function ActivityTicker() {
  const { data, error, isLoading, mutate } = useApi<{ logs: AuditLogEntry[] }>("/api/audit-logs");
  const logs = data?.logs || [];

  // Audit rows are virtual-dated. Against the real clock these render negative.
  const { timeAgo } = useVirtualDate();

  return (
    <div className="glass-panel p-5 h-full flex flex-col">
      <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-widest flex items-center gap-2">
        <span className="text-[#8B5CF6]">⚡</span> Live Activity Feed
      </h3>
      
      <div className="flex-1 max-h-[400px] overflow-y-auto no-scrollbar space-y-3 pr-2">
        <QueryBoundary
          error={error}
          loading={isLoading}
          isEmpty={logs.length === 0}
          emptyMessage="No recent activity."
          onRetry={() => mutate()}
        >
          {logs.map((log) => {
            const config = EVENT_TYPE_CONFIG[log.event_type] || { color: "text-gray-400", icon: "•" };
            return (
              <Link key={log.id} href={`/invoices/${log.invoice_id}`} className="block group">
                <div className="p-3 rounded-lg bg-white/5 border border-white/5 group-hover:bg-white/10 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <span className={`text-base ${config.color} shrink-0`}>{config.icon}</span>
                      <div>
                        <p className="text-sm text-white/90">
                          <span className="font-bold text-white mr-2">{log.client_name || `Inv #${log.invoice_id}`}</span>
                          <span className="text-white/70 line-clamp-1 text-xs mt-0.5">{log.action_taken}</span>
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-white/40 shrink-0 mt-1 whitespace-nowrap">
                      {timeAgo(log.timestamp)}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </QueryBoundary>
      </div>
    </div>
  );
}
