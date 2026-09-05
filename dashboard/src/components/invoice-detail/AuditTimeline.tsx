"use client";
import { useApi } from "@/hooks/useApi";
import { AuditLogEntry } from "@/lib/types";
import AuditTimelineEntry from "./AuditTimelineEntry";
import QueryBoundary from "@/components/QueryBoundary";

export default function AuditTimeline({ invoiceId }: { invoiceId: number }) {
  const { data, error, isLoading, mutate } = useApi<{ trail: AuditLogEntry[] }>(
    `/api/invoices/${invoiceId}/audit-logs`
  );
  const trail = data?.trail || [];

  return (
    <div className="mt-6 ml-2">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-[#00F0FF]">▼</span> Audit Timeline
      </h3>
      <div className="pl-2">
        <QueryBoundary
          error={error}
          loading={isLoading}
          isEmpty={trail.length === 0}
          emptyMessage="No audit logs found for this invoice. Advance the simulation."
          onRetry={() => mutate()}
        >
          {trail.map((entry, idx) => (
            <AuditTimelineEntry
              key={entry.id}
              entry={entry}
              nextEntry={trail[idx + 1]}
            />
          ))}
        </QueryBoundary>
      </div>
    </div>
  );
}
