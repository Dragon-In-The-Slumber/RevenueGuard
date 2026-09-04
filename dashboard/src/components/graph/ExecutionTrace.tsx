"use client";
import { useApi } from "@/hooks/useApi";
import { AuditLogEntry } from "@/lib/types";
import { EVENT_TYPE_CONFIG } from "@/lib/constants";
import Link from "next/link";

export default function ExecutionTrace() {
  const { data } = useApi<{ logs: AuditLogEntry[] }>("/api/audit-logs");
  const logs = data?.logs || [];

  // Reconstruct a path from the most recent logs (simulating a single execution trace)
  // For demo, we just take the last 5 logs and reverse them to show chronological order
  const path = logs.slice(0, 6).reverse();

  if (path.length === 0) return null;

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
          <span className="text-[#00F0FF]">⎍</span> Recent Execution Trace
        </h3>
        {path[0] && (
          <div className="text-xs font-mono text-white/50 bg-white/5 px-3 py-1 rounded-full border border-white/10">
            Invoice <Link href={`/invoices/${path[path.length - 1].invoice_id}`} className="text-[#00F0FF] hover:underline">#{path[path.length - 1].invoice_id}</Link> ({path[path.length - 1].client_name})
          </div>
        )}
      </div>

      <div className="glass-panel p-4 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-2 min-w-max">
          {path.map((step, idx) => {
            const config = EVENT_TYPE_CONFIG[step.event_type] || { color: "text-gray-400", icon: "•" };
            
            return (
              <div key={step.id} className="flex items-center">
                <div className={`
                  flex flex-col items-center justify-center p-3 rounded-lg border bg-white/[0.02] 
                  min-w-[140px] relative group hover:bg-white/[0.05] transition-colors
                  ${step.compliance_verdict === "FAIL" ? "border-red-500/30" : "border-white/10"}
                `}>
                  <span className={`text-xl mb-1 ${config.color}`}>{config.icon}</span>
                  <span className="text-[10px] font-mono font-bold text-white/80 whitespace-nowrap">
                    {step.event_type}
                  </span>
                  
                  {/* Tooltip */}
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-48 bg-black/90 border border-white/20 p-2 rounded text-[10px] text-white/70 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-2xl backdrop-blur-xl">
                    <p className="font-bold text-white mb-1">{step.action_taken}</p>
                    {step.agent_reasoning && <p className="font-mono text-cyan-300 truncate">{step.agent_reasoning}</p>}
                    <p className="text-white/40 mt-1">{new Date(step.timestamp).toLocaleTimeString()}</p>
                  </div>
                </div>

                {idx < path.length - 1 && (
                  <div className="w-8 h-[2px] bg-white/10 relative">
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 border-t-2 border-r-2 border-white/30 rotate-45" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
