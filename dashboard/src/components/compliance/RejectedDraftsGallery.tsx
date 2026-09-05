"use client";
import { useApi } from "@/hooks/useApi";
import { AuditLogEntry } from "@/lib/types";
import ComplianceDiff from "@/components/invoice-detail/ComplianceDiff";
import QueryBoundary from "@/components/QueryBoundary";
import Link from "next/link";

export default function RejectedDraftsGallery() {
  const { data, error, isLoading, mutate } = useApi<{ rejected: AuditLogEntry[] }>("/api/compliance/rejected");
  const rejected = data?.rejected || [];

  return (
    <div className="glass-panel p-6">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-red-400">🛡️</span> Rejected Drafts Gallery
      </h3>

      <QueryBoundary
        error={error}
        loading={isLoading}
        isEmpty={rejected.length === 0}
        emptyMessage="No compliance violations recorded yet."
        onRetry={() => mutate()}
      >
        <div className="space-y-6 max-h-[600px] overflow-y-auto no-scrollbar pr-2">
          {rejected.map((log) => (
            <div key={log.id} className="bg-white/[0.02] border border-white/5 p-5 rounded-xl">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <p className="text-xs text-white/50 mb-1">
                    {new Date(log.timestamp).toLocaleString()}
                  </p>
                  <Link href={`/invoices/${log.invoice_id}`} className="text-sm font-bold text-white hover:text-[#00F0FF] transition-colors">
                    {log.client_name} (Invoice #{log.invoice_id})
                  </Link>
                </div>
              </div>
              
              <ComplianceDiff 
                originalContent={log.content_snapshot || ""}
                reasoning={log.agent_reasoning || "Failed compliance"}
                ruleApplied={log.rule_applied}
                approvedContent={log.approved_content}
              />
            </div>
          ))}
        </div>
      </QueryBoundary>
    </div>
  );
}
