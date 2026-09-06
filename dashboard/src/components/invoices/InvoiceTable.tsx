"use client";
import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { Invoice } from "@/lib/types";
import { STATUS_CONFIG } from "@/lib/constants";
import StatusBadge from "./StatusBadge";
import EscalationProgress from "./EscalationProgress";
import QuickActions from "./QuickActions";
import QueryBoundary from "@/components/QueryBoundary";
import { useVirtualDate } from "@/hooks/useVirtualDate";
import { useRouter } from "next/navigation";

export default function InvoiceTable() {
  const { data, error, isLoading, mutate } = useApi<{ invoices: Invoice[] }>("/api/invoices");
  const invoices = data?.invoices || [];
  const router = useRouter();
  const { daysOverdue } = useVirtualDate();

  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  
  // Client-side filtering
  const filteredInvoices = invoices.filter(inv => {
    const matchesSearch = inv.client_name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = filterStatus === "ALL" || inv.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="glass-panel overflow-hidden flex flex-col h-[calc(100vh-200px)]">
      {/* Controls */}
      <div className="p-4 border-b border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4 bg-white/[0.02]">
        <div className="flex items-center gap-4 w-full sm:w-auto">
          <select 
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-black/40 border border-white/10 text-white text-sm rounded-lg px-3 py-2 outline-none focus:border-accent-primary transition-colors"
          >
            <option value="ALL">All Statuses</option>
            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
              <option key={key} value={key}>{config.icon} {config.label}</option>
            ))}
          </select>
          <div className="text-white/40 font-mono text-sm">
            {filteredInvoices.length} results
          </div>
        </div>
        
        <div className="relative w-full sm:w-64">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30">🔍</span>
          <input 
            type="text" 
            placeholder="Search clients..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-black/40 border border-white/10 text-white text-sm rounded-lg pl-9 pr-3 py-2 outline-none focus:border-accent-primary transition-colors"
          />
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto no-scrollbar relative">
        <QueryBoundary
          error={error}
          loading={isLoading}
          isEmpty={invoices.length === 0}
          emptyMessage="No invoices found. Generate a batch from the Command Center."
          onRetry={() => mutate()}
          loadingFallback={
            <div className="space-y-2 p-4">
              {[0, 1, 2, 3, 4].map((i) => (
                <div key={i} className="h-12 animate-pulse rounded bg-white/5" />
              ))}
            </div>
          }
        >
        <table className="w-full text-left text-sm text-white border-collapse">
          <thead className="sticky top-0 bg-bg-deep/90 backdrop-blur-md z-20 shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
            <tr>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal">ID</th>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal">Client</th>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal">Amount</th>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal">Due Date</th>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal">Overdue</th>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal">Status</th>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal">Stage</th>
              <th className="px-6 py-4 font-mono text-xs uppercase tracking-wider text-white/50 border-b border-white/5 font-normal text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filteredInvoices.map((inv) => (
              <tr 
                key={inv.id} 
                onClick={(e) => {
                  // Prevent navigation if clicking on actions
                  if ((e.target as HTMLElement).closest('button') || (e.target as HTMLElement).closest('a')) return;
                  router.push(`/invoices/${inv.id}`);
                }}
                className="group hover:bg-white/[0.02] transition-colors cursor-pointer"
              >
                <td className="px-6 py-4 font-mono text-white/40">#{inv.id}</td>
                <td className="px-6 py-4">
                  <p className="font-bold text-white group-hover:text-accent-primary transition-colors">{inv.client_name}</p>
                  <p className="text-xs text-white/40">{inv.client_email}</p>
                </td>
                <td className="px-6 py-4 font-mono">₹{inv.amount.toLocaleString('en-IN')}</td>
                <td className="px-6 py-4">
                  <p className="text-white/80">{inv.due_date ? new Date(inv.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '-'}</p>
                </td>
                <td className="px-6 py-4 font-mono">
                  {inv.due_date ? (
                    (() => {
                      // Virtual clock: status transitions run on it, so overdue must too.
                      const days = daysOverdue(inv.due_date);
                      if (days === null || days <= 0) return <span className="text-white/30">-</span>;
                      return <span className={days > 30 ? "text-red-400" : "text-amber-400"}>{days}d</span>;
                    })()
                  ) : "-"}
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={inv.status} />
                </td>
                <td className="px-6 py-4">
                  <EscalationProgress stage={inv.escalation_stage} />
                </td>
                <td className="px-6 py-4">
                  <QuickActions invoiceId={inv.id} />
                </td>
              </tr>
            ))}
            {filteredInvoices.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-white/30 font-mono text-sm">
                  No invoices match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </QueryBoundary>
      </div>
    </div>
  );
}
