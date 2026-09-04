"use client";
import { useState } from "react";
import { apiPost } from "@/lib/api";
import Link from "next/link";

export default function QuickActions({ invoiceId }: { invoiceId: number }) {
  const [loading, setLoading] = useState(false);

  const handleSimulateReply = async () => {
    const msg = prompt("Simulate client email reply:");
    if (!msg) return;
    
    try {
      setLoading(true);
      await apiPost(`/api/invoices/${invoiceId}/reply`, { message: msg });
      alert("Reply sent! Check audit logs or advance timeline.");
    } catch (e) {
      console.error(e);
      alert("Failed to send reply");
    } finally {
      setLoading(false);
    }
  };

  const handleSimulatePay = async () => {
    try {
      setLoading(true);
      await apiPost(`/api/webhooks/razorpay`, { 
        event: "invoice.paid", 
        payload: { invoice_id: String(invoiceId) } 
      });
      alert("Payment webhook fired!");
    } catch (e) {
      console.error(e);
      alert("Failed to fire webhook");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-end gap-2">
      <button 
        onClick={handleSimulateReply}
        disabled={loading}
        className="w-8 h-8 rounded bg-white/5 hover:bg-white/10 flex items-center justify-center text-cyan-400 transition-colors tooltip-trigger"
        title="Simulate Reply"
      >
        💬
      </button>
      <button 
        onClick={handleSimulatePay}
        disabled={loading}
        className="w-8 h-8 rounded bg-white/5 hover:bg-white/10 flex items-center justify-center text-emerald-400 transition-colors tooltip-trigger"
        title="Simulate Payment"
      >
        💰
      </button>
      <Link 
        href={`/invoices/${invoiceId}`}
        className="w-8 h-8 rounded bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/70 hover:text-white transition-colors tooltip-trigger"
        title="View Audit Trail"
      >
        📋
      </Link>
    </div>
  );
}
