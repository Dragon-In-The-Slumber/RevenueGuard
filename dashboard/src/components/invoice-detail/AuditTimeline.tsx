"use client";
import { useApi } from "@/hooks/useApi";
import { AuditLogEntry } from "@/lib/types";
import AuditTimelineEntry from "./AuditTimelineEntry";

export default function AuditTimeline({ invoiceId }: { invoiceId: number }) {
  const { data } = useApi<{ trail: AuditLogEntry[] }>(`/api/invoices/${invoiceId}/audit-logs`);
  const trail = data?.trail || [];

  if (trail.length === 0) {
    return (
      <div className="glass-panel p-8 text-center text-white/30 font-mono text-sm mt-6">
        No audit logs found for this invoice.
      </div>
    );
  }

  return (
    <div className="mt-6 ml-2">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-[#00F0FF]">▼</span> Audit Timeline
      </h3>
      <div className="pl-2">
        {trail.map((entry, idx) => (
          <AuditTimelineEntry 
            key={entry.id} 
            entry={entry} 
            nextEntry={trail[idx + 1]} 
          />
        ))}
      </div>
    </div>
  );
}
