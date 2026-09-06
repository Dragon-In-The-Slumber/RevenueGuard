"use client";
import { useApi } from "@/hooks/useApi";
import { AuditLogEntry } from "@/lib/types";
import ComplianceDiff from "@/components/invoice-detail/ComplianceDiff";
import { COMPLIANCE_CONFIG } from "@/lib/constants";
import QueryBoundary from "@/components/QueryBoundary";
import Link from "next/link";

export default function RejectedDraftsGallery() {
  const { data, error, isLoading, mutate } = useApi<{ rejected: AuditLogEntry[] }>("/api/compliance/rejected");
  const rejected = data?.rejected || [];

  return (
    <div className="glass-panel p-6">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-red-400">🛡️</span> Compliance Exceptions
      </h3>

      <QueryBoundary
        error={error}
        loading={isLoading}
        isEmpty={rejected.length === 0}
        emptyMessage="No compliance exceptions recorded yet."
        onRetry={() => mutate()}
      >
        <div className="space-y-6 max-h-[600px] overflow-y-auto no-scrollbar pr-2">
          {rejected.map((log) => {
            const verdict = log.compliance_verdict || "FAIL";
            const config = COMPLIANCE_CONFIG[verdict] ?? COMPLIANCE_CONFIG.FAIL;
            return (
              <div
                key={log.id}
                className={`bg-white/[0.02] border p-5 rounded-xl ${config.border}`}
              >
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <p className="text-xs text-white/50 mb-1">
                      {new Date(log.timestamp).toLocaleString()}
                    </p>
                    <Link href={`/invoices/${log.invoice_id}`} className="text-sm font-bold text-white hover:text-accent-primary transition-colors">
                      {log.client_name} (Invoice #{log.invoice_id})
                    </Link>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${config.bg} ${config.color} ${config.border}`}
                  >
                    {config.label}
                  </span>
                </div>

                <ComplianceDiff
                  originalContent={log.content_snapshot || ""}
                  reasoning={log.agent_reasoning || "Failed compliance"}
                  ruleApplied={log.rule_applied}
                  approvedContent={log.approved_content}
                  verdict={verdict}
                  verdictSource={log.verdict_source}
                />
              </div>
            );
          })}
        </div>
      </QueryBoundary>
    </div>
  );
}
