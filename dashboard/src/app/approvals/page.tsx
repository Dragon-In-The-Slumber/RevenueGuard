"use client";
import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { apiPost } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";
import QueryBoundary from "@/components/QueryBoundary";
import StatusBadge from "@/components/invoices/StatusBadge";
import { InvoiceStatus } from "@/lib/types";
import Link from "next/link";
import { useSWRConfig } from "swr";

interface Approval {
  invoice_id: number;
  client_name: string;
  amount: number;
  status: InvoiceStatus;
  escalation_stage: string;
  contact_attempts: number;
  relationship_score: number;
  reason: string;
  detail: string | null;
  agent_proposed: string | null;
  agent_reasoning: string | null;
  guard_veto: string | null;
  guard_detail: string | null;
}

export default function ApprovalsPage() {
  const { data, error, isLoading, mutate } = useApi<{ approvals: Approval[] }>("/api/approvals");
  const approvals = data?.approvals || [];
  const { addToast } = useToast();
  const { mutate: globalMutate } = useSWRConfig();
  const [busy, setBusy] = useState<number | null>(null);
  const [notes, setNotes] = useState<Record<number, string>>({});

  const decide = async (id: number, verdict: "approve" | "reject") => {
    try {
      setBusy(id);
      const res = await apiPost<{ old_status: string; new_status: string }>(
        `/api/approvals/${id}/${verdict}`,
        { note: notes[id] || "" }
      );
      addToast(
        `Invoice #${id}: ${res.old_status} → ${res.new_status}`,
        verdict === "approve" ? "success" : "info"
      );
      mutate();
      globalMutate("/api/invoices");
      globalMutate("/api/metrics");
    } catch (e) {
      addToast(e instanceof Error ? e.message : "Decision failed", "error");
    } finally {
      setBusy(null);
    }
  };

  const totalValue = approvals.reduce((n, a) => n + a.amount, 0);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Approval Queue</h1>
        <p className="text-white/50 text-sm font-mono max-w-3xl">
          Cases the agent handed to a person — stage gates, policy vetoes and disputes.
          Each carries the agent&apos;s own case, so a reviewer decides on the same
          information the agent had.
        </p>
      </div>

      {approvals.length > 0 && (
        <div className="flex gap-4">
          <div className="glass-panel px-5 py-3">
            <p className="mono-label text-white/40">Awaiting review</p>
            <p className="text-2xl font-mono font-bold text-white">{approvals.length}</p>
          </div>
          <div className="glass-panel px-5 py-3">
            <p className="mono-label text-white/40">Value held</p>
            <p className="text-2xl font-mono font-bold text-amber-400">
              ₹{totalValue.toLocaleString("en-IN")}
            </p>
          </div>
        </div>
      )}

      <QueryBoundary
        error={error}
        loading={isLoading}
        isEmpty={approvals.length === 0}
        emptyMessage="Nothing awaiting human review. The agent is operating inside its limits."
        onRetry={() => mutate()}
      >
        <div className="space-y-4">
          {approvals.map((a) => (
            <div key={a.invoice_id} className="glass-panel p-5">
              <div className="flex items-start justify-between gap-6 mb-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <Link
                      href={`/invoices/${a.invoice_id}`}
                      className="text-base font-bold text-white hover:text-accent-primary transition-colors"
                    >
                      {a.client_name}
                    </Link>
                    <StatusBadge status={a.status} />
                    <span className="text-[10px] font-mono text-white/30">
                      #{a.invoice_id} · {a.escalation_stage} · {a.contact_attempts} contacts
                    </span>
                  </div>
                  <p className="text-xs font-mono text-amber-400">{a.reason}</p>
                  {a.detail && <p className="text-xs text-white/50 mt-1">{a.detail}</p>}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xl font-mono font-bold text-white">
                    ₹{a.amount.toLocaleString("en-IN")}
                  </p>
                  {a.relationship_score < 1.0 && (
                    <p className="text-[10px] font-mono text-red-400 mt-1">
                      relationship {a.relationship_score}
                    </p>
                  )}
                </div>
              </div>

              {/* The agent's case, and the guard's objection if there was one. */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                {a.agent_reasoning && (
                  <div className="rounded-lg border border-purple-400/25 bg-purple-500/5 p-3">
                    <p className="mono-label text-purple-300 mb-1">Agent proposed</p>
                    {a.agent_proposed && (
                      <p className="text-xs font-mono text-white/80 mb-1">{a.agent_proposed}</p>
                    )}
                    <p className="text-xs text-white/60 leading-relaxed">{a.agent_reasoning}</p>
                  </div>
                )}
                {a.guard_veto && (
                  <div className="rounded-lg border border-amber-400/25 bg-amber-500/5 p-3">
                    <p className="mono-label text-amber-300 mb-1">Policy guard blocked it</p>
                    <p className="text-xs font-mono text-white/80 mb-1">{a.guard_veto}</p>
                    {a.guard_detail && (
                      <p className="text-xs text-white/60 leading-relaxed">{a.guard_detail}</p>
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={notes[a.invoice_id] || ""}
                  onChange={(e) => setNotes({ ...notes, [a.invoice_id]: e.target.value })}
                  placeholder="Decision note (recorded in the audit trail)…"
                  className="flex-1 bg-black/40 border border-white/10 rounded px-3 py-1.5 text-xs text-white outline-none focus:border-accent-primary"
                />
                <button
                  onClick={() => decide(a.invoice_id, "approve")}
                  disabled={busy === a.invoice_id}
                  className="px-4 py-1.5 text-xs font-bold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
                >
                  Approve &amp; resume
                </button>
                <button
                  onClick={() => decide(a.invoice_id, "reject")}
                  disabled={busy === a.invoice_id}
                  className="px-4 py-1.5 text-xs font-bold rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors disabled:opacity-50"
                >
                  Halt collection
                </button>
              </div>
            </div>
          ))}
        </div>
      </QueryBoundary>
    </div>
  );
}
