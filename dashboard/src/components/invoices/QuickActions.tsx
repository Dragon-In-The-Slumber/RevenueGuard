"use client";
import { useState } from "react";
import { fireWebhook, sendClientReply } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";
import Link from "next/link";

export default function QuickActions({ invoiceId }: { invoiceId: number }) {
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  const handleSimulateReply = async () => {
    const msg = prompt("Simulate client email reply:");
    if (!msg) return;

    try {
      setLoading(true);
      const res = await sendClientReply(invoiceId, msg);
      addToast(
        `Classified ${res.intent ?? "UNKNOWN"} — ${res.old_status} → ${res.new_status}`,
        res.old_status === res.new_status ? "info" : "success"
      );
    } catch (e) {
      addToast(e instanceof Error ? e.message : "Failed to send reply", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleSimulatePay = async () => {
    try {
      setLoading(true);
      const res = await fireWebhook("invoice.paid", invoiceId);
      addToast(`Invoice #${res.invoice_id}: ${res.old_status} → ${res.new_status}`, "success");
    } catch (e) {
      addToast(e instanceof Error ? e.message : "Failed to fire webhook", "error");
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
