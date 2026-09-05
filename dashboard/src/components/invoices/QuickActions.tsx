"use client";
import { useState } from "react";
import { fireWebhook, sendClientReply } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";
import Link from "next/link";

export default function QuickActions({ invoiceId }: { invoiceId: number }) {
  const [loading, setLoading] = useState(false);
  const [composing, setComposing] = useState(false);
  const [reply, setReply] = useState("");
  const { addToast } = useToast();

  // An inline composer rather than a native prompt(): the browser dialog is
  // jarring against the glass design, blocks the page, and cannot be styled.
  const handleSimulateReply = async () => {
    const msg = reply.trim();
    if (!msg) return;

    try {
      setLoading(true);
      const res = await sendClientReply(invoiceId, msg);
      addToast(
        `Classified ${res.intent ?? "UNKNOWN"} — ${res.old_status} → ${res.new_status}`,
        res.old_status === res.new_status ? "info" : "success"
      );
      setReply("");
      setComposing(false);
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

  if (composing) {
    return (
      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          type="text"
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSimulateReply();
            if (e.key === "Escape") { setComposing(false); setReply(""); }
          }}
          placeholder="Client reply…"
          className="w-56 bg-black/40 border border-[#00F0FF]/40 rounded px-2 py-1 text-xs text-white outline-none"
        />
        <button
          onClick={handleSimulateReply}
          disabled={loading || !reply.trim()}
          className="px-2 py-1 rounded bg-[#00F0FF]/20 text-[#00F0FF] text-[10px] font-bold uppercase tracking-wider disabled:opacity-40"
        >
          Send
        </button>
        <button
          onClick={() => { setComposing(false); setReply(""); }}
          className="px-2 py-1 rounded bg-white/5 text-white/50 text-[10px] uppercase tracking-wider"
        >
          Esc
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-end gap-2">
      <button 
        onClick={() => setComposing(true)}
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
