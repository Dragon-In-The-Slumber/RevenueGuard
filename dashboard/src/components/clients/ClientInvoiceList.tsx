"use client";
import { useApi } from "@/hooks/useApi";
import { Invoice } from "@/lib/types";
import StatusBadge from "@/components/invoices/StatusBadge";
import Link from "next/link";
import EscalationProgress from "@/components/invoices/EscalationProgress";

export default function ClientInvoiceList({ clientName }: { clientName: string }) {
  const { data } = useApi<{ invoices: Invoice[] }>("/api/invoices");
  
  if (!data) return <div className="glass-panel p-6 animate-pulse h-64"></div>;

  const clientInvoices = data.invoices.filter(inv => inv.client_name === clientName);

  return (
    <div className="glass-panel overflow-hidden">
      <div className="p-4 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
        <h3 className="text-sm font-bold text-white uppercase tracking-widest">
          Active Invoices for {clientName}
        </h3>
        <div className="flex gap-2">
          {['OVERDUE', 'ESCALATED', 'DISPUTE', 'RECOVERED'].map(status => {
            const count = clientInvoices.filter(i => i.status === status).length;
            if (count === 0) return null;
            return (
              <div key={status} className="flex flex-col items-center bg-black/40 px-3 py-1 rounded border border-white/5">
                <span className="text-white font-bold text-sm">{count}</span>
                <span className="text-[8px] uppercase tracking-wider text-white/50">{status}</span>
              </div>
            );
          })}
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-white">
          <thead>
            <tr>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-white/30 border-b border-white/5">ID</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-white/30 border-b border-white/5">Amount</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-white/30 border-b border-white/5">Status</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-white/30 border-b border-white/5">Stage</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-white/30 border-b border-white/5 text-right">View</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {clientInvoices.map(inv => (
              <tr key={inv.id} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-3 font-mono text-white/50">#{inv.id}</td>
                <td className="px-4 py-3 font-mono">₹{inv.amount.toLocaleString()}</td>
                <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                <td className="px-4 py-3"><EscalationProgress stage={inv.escalation_stage} /></td>
                <td className="px-4 py-3 text-right">
                  <Link href={`/invoices/${inv.id}`} className="text-[#00F0FF] hover:underline text-xs">
                    Details →
                  </Link>
                </td>
              </tr>
            ))}
            {clientInvoices.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-white/30 text-xs font-mono">
                  No invoices found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
