"use client";
import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import QueryBoundary from "@/components/QueryBoundary";

interface Outcome { event: string; what: string; detail: string | null; rule: string | null }
interface ToolCall { call: string; why: string | null }
interface Compliance { verdict: string; reason: string | null }
interface Guard { rule: string | null; detail: string | null; substitution: string | null }

interface Decision {
  timestamp: string;
  chose: string;
  reasoning: string | null;
  considered: string;
  expected_outcome: string | null;
  source: string | null;
  guard: Guard | null;
  tools: ToolCall[];
  compliance: Compliance[];
  outcomes: Outcome[];
}

interface DecisionsResponse {
  decision_count: number;
  relationship_score: number;
  decisions: Decision[];
}

const OUTCOME_TONE: Record<string, string> = {
  PAYMENT_RECEIVED: "text-emerald-400",
  NO_RESPONSE: "text-white/40",
  INTENT_CLASSIFIED: "text-cyan-400",
  EMAIL_SENT: "text-white/70",
  AGENT_WAIT: "text-amber-400",
  HUMAN_ESCALATED: "text-pink-400",
  RELATIONSHIP_DAMAGED: "text-red-400",
  PTP_BROKEN: "text-red-400",
};

/** Marks a decision that came from a deterministic policy rather than the model. */
function SourceTag({ source }: { source: string | null }) {
  if (!source) return null;
  const isModel = source === "llm" || source === "llm_cached";
  return (
    <span
      className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase tracking-wider border ${
        isModel
          ? "bg-purple-500/15 text-purple-300 border-purple-400/30"
          : "bg-white/5 text-white/40 border-white/10"
      }`}
      title={isModel ? "Chosen by the model" : "Chosen by the deterministic fallback policy"}
    >
      {isModel ? "model" : "policy"}
    </span>
  );
}

export default function DecisionExplorer({ invoiceId }: { invoiceId: number }) {
  const { data, error, isLoading, mutate } = useApi<DecisionsResponse>(
    `/api/invoices/${invoiceId}/decisions`
  );
  const [open, setOpen] = useState<number | null>(0);
  const decisions = data?.decisions || [];

  return (
    <div className="glass-panel p-5 mt-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
          <span className="text-purple-400">◆</span> Decision Explorer
        </h3>
        {data && (
          <span className="text-[10px] font-mono text-white/40">
            {data.decision_count} decision{data.decision_count === 1 ? "" : "s"}
            {data.relationship_score < 1 && ` · relationship ${data.relationship_score}`}
          </span>
        )}
      </div>

      <QueryBoundary
        error={error}
        loading={isLoading}
        isEmpty={decisions.length === 0}
        emptyMessage="No decisions yet. Advance the simulation."
        onRetry={() => mutate()}
      >
        <div className="space-y-3">
          {decisions.map((d, i) => {
            const expanded = open === i;
            return (
              <div
                key={i}
                className={`rounded-xl border transition-colors ${
                  d.guard ? "border-amber-400/30 bg-amber-500/[0.03]" : "border-white/10 bg-white/[0.02]"
                }`}
              >
                <button
                  onClick={() => setOpen(expanded ? null : i)}
                  className="w-full text-left p-4 flex items-start justify-between gap-4"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-[10px] font-mono text-white/30">
                        {d.timestamp.slice(0, 10)}
                      </span>
                      <SourceTag source={d.source} />
                      {d.guard && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-400/30">
                          vetoed
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-bold text-white">{d.chose}</p>
                  </div>
                  <span className="text-white/30 text-xs shrink-0 mt-1">{expanded ? "▲" : "▼"}</span>
                </button>

                {expanded && (
                  <div className="px-4 pb-4 space-y-3">
                    {/* Considered → chose → why */}
                    {d.considered && (
                      <div>
                        <p className="mono-label text-white/30 mb-1">Alternatives considered</p>
                        <p className="text-xs font-mono text-white/50">{d.considered}</p>
                      </div>
                    )}
                    {d.reasoning && (
                      <div className="rounded-lg border border-purple-400/20 bg-purple-500/5 p-3">
                        <p className="mono-label text-purple-300 mb-1">Why</p>
                        <p className="text-xs text-white/75 leading-relaxed">{d.reasoning}</p>
                      </div>
                    )}
                    {d.expected_outcome && (
                      <div>
                        <p className="mono-label text-white/30 mb-1">Agent predicted</p>
                        <p className="text-xs text-white/60 italic">{d.expected_outcome}</p>
                      </div>
                    )}

                    {/* What the guard said */}
                    {d.guard && (
                      <div className="rounded-lg border border-amber-400/25 bg-amber-500/5 p-3">
                        <p className="mono-label text-amber-300 mb-1">Policy guard</p>
                        <p className="text-xs font-mono text-white/80">{d.guard.rule}</p>
                        {d.guard.detail && (
                          <p className="text-xs text-white/60 mt-1">{d.guard.detail}</p>
                        )}
                        {d.guard.substitution && (
                          <p className="text-xs text-amber-200/80 mt-1">{d.guard.substitution}</p>
                        )}
                      </div>
                    )}

                    {d.compliance.length > 0 && (
                      <div>
                        <p className="mono-label text-white/30 mb-1">Compliance</p>
                        {d.compliance.map((c, ci) => (
                          <p key={ci} className="text-xs">
                            <span className={c.verdict === "PASS" ? "text-emerald-400" : "text-red-400"}>
                              {c.verdict}
                            </span>
                            <span className="text-white/50"> — {c.reason?.slice(0, 160)}</span>
                          </p>
                        ))}
                      </div>
                    )}

                    {d.tools.length > 0 && (
                      <div>
                        <p className="mono-label text-white/30 mb-1">Tools called</p>
                        {d.tools.map((t, ti) => (
                          <p key={ti} className="text-[11px] font-mono text-cyan-300/70 break-all">
                            {t.call}
                          </p>
                        ))}
                      </div>
                    )}

                    {/* What actually happened */}
                    {d.outcomes.length > 0 && (
                      <div className="border-t border-white/5 pt-3">
                        <p className="mono-label text-white/30 mb-1">What happened</p>
                        {d.outcomes.map((o, oi) => (
                          <div key={oi} className="mb-1">
                            <p className={`text-xs font-mono ${OUTCOME_TONE[o.event] || "text-white/60"}`}>
                              {o.event} · {o.what}
                            </p>
                            {o.detail && (
                              <p className="text-[11px] text-white/40 leading-relaxed">{o.detail}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </QueryBoundary>
    </div>
  );
}
