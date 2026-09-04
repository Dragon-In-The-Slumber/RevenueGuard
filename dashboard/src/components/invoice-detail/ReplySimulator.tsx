"use client";
import { useState } from "react";
import { apiPost } from "@/lib/api";

export default function ReplySimulator({ invoiceId }: { invoiceId: number }) {
  const [loading, setLoading] = useState(false);
  const [customText, setCustomText] = useState("");

  const sendReply = async (message: string) => {
    if (!message.trim()) return;
    try {
      setLoading(true);
      await apiPost(`/api/invoices/${invoiceId}/reply`, { message });
      alert("Reply sent! Check Audit Timeline for intent classification.");
      setCustomText("");
    } catch (e) {
      console.error(e);
      alert("Failed to send reply");
    } finally {
      setLoading(false);
    }
  };

  const simulateWebhook = async (event: string) => {
    try {
      setLoading(true);
      await apiPost(`/api/webhooks/razorpay`, { 
        event, 
        payload: { invoice_id: String(invoiceId) } 
      });
      alert(`Webhook ${event} fired!`);
    } catch (e) {
      console.error(e);
      alert("Failed to fire webhook");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel p-5 mt-6 border-t-[3px] border-[#00F0FF]/30">
      <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-widest flex items-center gap-2">
        <span className="text-[#00F0FF]">🎮</span> Interactive Simulator
      </h3>

      <div className="space-y-6">
        {/* Quick Replies */}
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-2">Simulate Client Reply</p>
          <div className="grid grid-cols-2 gap-2">
            <button 
              onClick={() => sendReply("We will pay by this Friday")}
              disabled={loading}
              className="px-3 py-2 text-xs text-left bg-white/5 hover:bg-white/10 rounded transition-colors text-white/80"
            >
              "We will pay Friday"
            </button>
            <button 
              onClick={() => sendReply("The amount billed is incorrect, we are disputing this invoice")}
              disabled={loading}
              className="px-3 py-2 text-xs text-left bg-white/5 hover:bg-white/10 rounded transition-colors text-white/80"
            >
              "Amount is wrong (Dispute)"
            </button>
            <button 
              onClick={() => sendReply("Please stop contacting us regarding this matter")}
              disabled={loading}
              className="px-3 py-2 text-xs text-left bg-white/5 hover:bg-white/10 rounded transition-colors text-white/80"
            >
              "Stop contacting us"
            </button>
            <button 
              onClick={() => sendReply("Can we get a two week extension on this payment?")}
              disabled={loading}
              className="px-3 py-2 text-xs text-left bg-white/5 hover:bg-white/10 rounded transition-colors text-white/80"
            >
              "Need 2-week extension"
            </button>
          </div>
          
          <div className="mt-3 flex gap-2">
            <input 
              type="text" 
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              placeholder="Custom client reply..."
              className="flex-1 bg-black/40 border border-white/10 rounded px-3 py-1.5 text-xs text-white outline-none focus:border-[#00F0FF]"
              onKeyDown={(e) => e.key === 'Enter' && sendReply(customText)}
            />
            <button 
              onClick={() => sendReply(customText)}
              disabled={loading || !customText.trim()}
              className="bg-[#00F0FF]/20 text-[#00F0FF] hover:bg-[#00F0FF]/30 px-3 py-1.5 rounded text-xs font-bold transition-colors disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>

        {/* Webhooks */}
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-2">Simulate Webhooks</p>
          <div className="flex flex-wrap gap-2">
            <button 
              onClick={() => simulateWebhook("invoice.paid")}
              disabled={loading}
              className="px-3 py-1.5 text-xs bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 rounded border border-emerald-500/20 transition-colors flex items-center gap-1.5"
            >
              <span>💰</span> Sim. Pay
            </button>
            <button 
              onClick={() => simulateWebhook("payment.dispute.created")}
              disabled={loading}
              className="px-3 py-1.5 text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded border border-red-500/20 transition-colors flex items-center gap-1.5"
            >
              <span>⚔️</span> Sim. Dispute
            </button>
            <button 
              onClick={() => simulateWebhook("payment.failed")}
              disabled={loading}
              className="px-3 py-1.5 text-xs bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded border border-amber-500/20 transition-colors flex items-center gap-1.5"
            >
              <span>❌</span> Sim. Fail
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
