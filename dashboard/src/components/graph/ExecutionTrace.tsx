"use client";
import { useApi } from "@/hooks/useApi";
import { AuditLogEntry } from "@/lib/types";
import { EVENT_TYPE_CONFIG } from "@/lib/constants";
import QueryBoundary from "@/components/QueryBoundary";
import { useWebSocketContext } from "@/components/WebSocketProvider";
import Link from "next/link";

/**
 * One invoice's real path through the graph.
 *
 * This used to slice the six most recent audit logs across ALL invoices and label
 * them "Invoice #N" — a cross-invoice slice presented as a single execution path.
 * Now it reads `visited_nodes` from the live tick, falling back to the GRAPH_PATH
 * audit row the tick persists.
 */
export default function ExecutionTrace() {
  const { traces, lastTickAt } = useWebSocketContext();
  const { data, error, isLoading, mutate } = useApi<{ logs: AuditLogEntry[] }>("/api/audit-logs");

  // Live trace from the socket wins; otherwise recover the last persisted path.
  const live = traces[0];
  const persisted = (data?.logs || []).find((l) => l.event_type === "GRAPH_PATH");

  const path: string[] = live
    ? live.nodes
    : persisted?.agent_reasoning
      ? persisted.agent_reasoning.split(" -> ")
      : [];

  const invoiceId = live?.invoice_id ?? persisted?.invoice_id ?? null;
  const clientName = live?.client_name ?? persisted?.client_name ?? null;
  const action = live?.action ?? null;

  if (error || isLoading) {
    return (
      <div className="mt-8">
        <QueryBoundary error={error} loading={isLoading} onRetry={() => mutate()}>
          {null}
        </QueryBoundary>
      </div>
    );
  }

  if (path.length === 0) return null;

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
          <span className="text-[#00F0FF]">⎍</span> Execution Trace
          {live && lastTickAt && (
            <span className="text-[10px] font-mono text-emerald-400 normal-case tracking-normal">
              live
            </span>
          )}
        </h3>
        {invoiceId !== null && (
          <div className="text-xs font-mono text-white/50 bg-white/5 px-3 py-1 rounded-full border border-white/10">
            Invoice{" "}
            <Link href={`/invoices/${invoiceId}`} className="text-[#00F0FF] hover:underline">
              #{invoiceId}
            </Link>
            {clientName ? ` (${clientName})` : ""}
            {action ? ` · ${action}` : ""}
          </div>
        )}
      </div>

      <div className="glass-panel p-4 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-2 min-w-max">
          {path.map((node, idx) => {
            const config = EVENT_TYPE_CONFIG[node] || { color: "text-cyan-400", icon: "◆" };
            const isDecision = node === "decide_action" || node === "validate_action";
            return (
              <div key={`${node}-${idx}`} className="flex items-center">
                <div
                  className={`flex flex-col items-center justify-center p-3 rounded-lg border bg-white/[0.02]
                  min-w-[150px] hover:bg-white/[0.05] transition-colors ${
                    isDecision ? "border-purple-400/40" : "border-white/10"
                  }`}
                >
                  <span className={`text-xl mb-1 ${isDecision ? "text-purple-400" : config.color}`}>
                    {isDecision ? "🎯" : config.icon}
                  </span>
                  <span className="text-[10px] font-mono font-bold text-white/80 whitespace-nowrap">
                    {node}
                  </span>
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
