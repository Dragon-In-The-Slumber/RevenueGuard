"use client";
import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { Invoice } from "@/lib/types";
import { apiFetch } from "@/lib/api";

const EVENT_TYPES = [
  { id: "invoice.paid", label: "Payment received in full" },
  { id: "invoice.partially_paid", label: "Partial payment received" },
  { id: "payment_link.paid", label: "Payment Link clicked and paid" },
  { id: "payment.dispute.created", label: "Formal dispute filed" },
  { id: "payment.failed", label: "Payment attempt failed" },
  { id: "virtual_account.credited", label: "Bank transfer received" }
];

export interface WebhookEventLog {
  id: string;
  timestamp: string;
  eventType: string;
  invoiceId: number;
  response: any;
  success: boolean;
}

export default function WebhookFirePanel({ onEventFired }: { onEventFired: (log: WebhookEventLog) => void }) {
  const { data } = useApi<{ invoices: Invoice[] }>("/api/invoices");
  const invoices = data?.invoices || [];
  
  const [selectedInvoice, setSelectedInvoice] = useState<string>("");
  const [selectedEvent, setSelectedEvent] = useState<string>(EVENT_TYPES[0].id);
  const [loading, setLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<{ success: boolean, data: any } | null>(null);

  const handleFireEvent = async () => {
    if (!selectedInvoice) return;
    
    setLoading(true);
    try {
      const payload = {
        event: selectedEvent,
        payload: {
          invoice: {
            entity: {
              id: `inv_${selectedInvoice}`,
              receipt: `rcpt_${selectedInvoice}`,
              status: selectedEvent.includes("paid") ? "paid" : "issued"
            }
          }
        }
      };

      const res = await apiFetch("/api/webhooks/razorpay", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      
      onEventFired({
        id: Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
        eventType: selectedEvent,
        invoiceId: parseInt(selectedInvoice),
        response: res,
        success: true
      });
      setLastResponse({ success: true, data: res });
    } catch (e: any) {
      onEventFired({
        id: Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
        eventType: selectedEvent,
        invoiceId: parseInt(selectedInvoice),
        response: { error: e.message || "Request failed" },
        success: false
      });
      setLastResponse({ success: false, data: { error: e.message || "Request failed" } });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel p-6">
      <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-widest flex items-center gap-2">
        <span className="text-[#00F0FF]">⚡</span> Fire Webhook Event
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-[10px] uppercase font-mono text-white/50 mb-2">Target Invoice</label>
          <select 
            className="w-full bg-black/40 border border-white/10 text-white rounded-lg px-4 py-2 outline-none focus:border-[#00F0FF] transition-colors"
            value={selectedInvoice}
            onChange={(e) => setSelectedInvoice(e.target.value)}
          >
            <option value="" disabled>Select an invoice...</option>
            {invoices.map(inv => (
              <option key={inv.id} value={inv.id.toString()}>
                #{inv.id} - {inv.client_name} (₹{inv.amount.toLocaleString()})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[10px] uppercase font-mono text-white/50 mb-2">Event Type</label>
          <select 
            className="w-full bg-black/40 border border-white/10 text-white rounded-lg px-4 py-2 outline-none focus:border-[#00F0FF] transition-colors"
            value={selectedEvent}
            onChange={(e) => setSelectedEvent(e.target.value)}
          >
            {EVENT_TYPES.map(evt => (
              <option key={evt.id} value={evt.id}>
                {evt.id} — {evt.label}
              </option>
            ))}
          </select>
        </div>

        <button 
          onClick={handleFireEvent}
          disabled={loading || !selectedInvoice}
          className="w-full mt-4 bg-[#00F0FF]/20 text-[#00F0FF] border border-[#00F0FF]/30 hover:bg-[#00F0FF]/30 px-6 py-3 rounded-lg font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs flex items-center justify-center gap-2"
        >
          {loading ? (
            <span className="animate-pulse">Firing...</span>
          ) : (
            <>
              <span>►</span> Fire Event
            </>
          )}
        </button>

        {lastResponse && (
          <div className={`mt-4 p-3 rounded text-xs font-mono border ${
            lastResponse.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}>
            <p className="font-bold mb-1">{lastResponse.success ? '✅ Webhook Accepted' : '❌ Webhook Failed'}</p>
            <p className="opacity-80 truncate">{JSON.stringify(lastResponse.data)}</p>
          </div>
        )}
      </div>
    </div>
  );
}
