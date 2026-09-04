"use client";
import { useApi } from "@/hooks/useApi";
import { Invoice } from "@/lib/types";

export default function CooldownBoard() {
  const { data } = useApi<{ invoices: Invoice[] }>("/api/invoices");
  const invoices = data?.invoices || [];

  // Filter active invoices
  const activeInvoices = invoices.filter(inv => !["RECOVERED", "LEGAL_HOLD", "UNRESPONSIVE", "DISPUTE", "PAUSED_PTP"].includes(inv.status));

  return (
    <div className="glass-panel p-6">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-amber-400">⏳</span> Cooldown Status
      </h3>

      <div className="space-y-4 max-h-[600px] overflow-y-auto no-scrollbar">
        {activeInvoices.map((inv) => {
          // For demo, we simulate a cooldown based on the virtual date or just random if not available
          // Since we don't have exact last_contacted_date from API, we'll mock it based on ID
          const daysSinceContact = (inv.id * 17) % 7; 
          const isReady = daysSinceContact >= 4;
          
          return (
            <div key={inv.id} className="bg-black/20 rounded p-3 flex items-center justify-between border border-white/5">
              <div>
                <p className="text-sm text-white font-bold">{inv.client_name}</p>
                <p className="text-[10px] text-white/50 font-mono">Invoice #{inv.id}</p>
              </div>
              
              <div className="text-right flex items-center gap-4">
                <div className="text-right">
                  <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-0.5">Next Contact</p>
                  <p className="text-xs text-white/80 font-mono">
                    {isReady ? "Now" : `In ${4 - daysSinceContact} days`}
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
        {activeInvoices.length === 0 && (
          <div className="text-center text-white/30 text-xs font-mono py-4">
            No active invoices subject to cooldown.
          </div>
        )}
      </div>
    </div>
  );
}
