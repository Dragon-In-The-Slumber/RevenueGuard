"use client";
import { useApi } from "@/hooks/useApi";
import { Invoice } from "@/lib/types";
import QueryBoundary from "@/components/QueryBoundary";
import { useVirtualDate } from "@/hooks/useVirtualDate";

export default function CooldownBoard() {
  const { data, error, isLoading, mutate } = useApi<{ invoices: Invoice[] }>("/api/invoices");
  const invoices = data?.invoices || [];
  const { daysSince } = useVirtualDate();

  // "the agent blocked itself N times" — the number that proves Pillar 2.
  const totalBlocked = invoices.reduce((n, i) => n + (i.escalations_blocked || 0), 0);

  // Filter active invoices
  const activeInvoices = invoices.filter(inv => !["RECOVERED", "LEGAL_HOLD", "UNRESPONSIVE", "DISPUTE", "PAUSED_PTP"].includes(inv.status));

  return (
    <div className="glass-panel p-6">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-amber-400">⏳</span> Cooldown Status
        {totalBlocked > 0 && (
          <span className="ml-auto text-[10px] font-mono text-emerald-400 normal-case tracking-normal">
            agent self-blocked {totalBlocked}x
          </span>
        )}
      </h3>

      <div className="space-y-4 max-h-[600px] overflow-y-auto no-scrollbar">
        <QueryBoundary
          error={error}
          loading={isLoading}
          isEmpty={activeInvoices.length === 0}
          emptyMessage="No active invoices subject to cooldown."
          onRetry={() => mutate()}
        >
        {activeInvoices.map((inv) => {
          // Real cooldown data from /api/invoices, computed against the virtual
          // clock. This panel exists to prove the frequency limit is enforced, so
          // it must not display a hash of the primary key.
          const daysSinceContact = daysSince(inv.last_contact_date);
          const isReady = daysSinceContact === null || daysSinceContact >= 4;
          const daysLeft = daysSinceContact === null ? 0 : Math.max(0, 4 - daysSinceContact);

          return (
            <div key={inv.id} className="bg-black/20 rounded p-3 flex items-center justify-between border border-white/5">
              <div>
                <p className="text-sm text-white font-bold">{inv.client_name}</p>
                <p className="text-[10px] text-white/50 font-mono">
                  Invoice #{inv.id}
                  {inv.last_contact_date
                    ? ` · last contact ${daysSinceContact}d ago`
                    : " · never contacted"}
                  {inv.escalations_blocked ? ` · blocked ${inv.escalations_blocked}x` : ""}
                </p>
              </div>
              
              <div className="text-right flex items-center gap-4">
                <div className="text-right">
                  <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-0.5">Next Contact</p>
                  <p className="text-xs text-white/80 font-mono">
                    {isReady ? "Now" : `In ${daysLeft} day${daysLeft === 1 ? "" : "s"}`}
                  </p>
                </div>
                
                {isReady ? (
                  <span className="bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded text-[10px] font-bold tracking-wider uppercase font-mono border border-emerald-500/20">
                    Ready
                  </span>
                ) : (
                  <span className="bg-amber-500/20 text-amber-400 px-2 py-1 rounded text-[10px] font-bold tracking-wider uppercase font-mono border border-amber-500/20">
                    Cooling
                  </span>
                )}
              </div>
            </div>
          );
        })}
        </QueryBoundary>
      </div>
    </div>
  );
}
