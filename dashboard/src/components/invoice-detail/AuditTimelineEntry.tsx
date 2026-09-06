"use client";
import { useState } from "react";
import { AuditLogEntry } from "@/lib/types";
import { EVENT_TYPE_CONFIG } from "@/lib/constants";
import EmailPreview from "./EmailPreview";
import ComplianceDiff from "./ComplianceDiff";

export default function AuditTimelineEntry({ entry, nextEntry }: { entry: AuditLogEntry, nextEntry?: AuditLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const config = EVENT_TYPE_CONFIG[entry.event_type] || { color: "text-gray-400", icon: "•" };

  const hasDetails = entry.agent_reasoning || entry.content_snapshot || entry.compliance_verdict;
  const isComplianceFail = entry.compliance_verdict === "FAIL";

  return (
    <div className="relative pl-8 py-4 border-l-2 border-white/10 last:border-transparent group">
      <div className={`absolute -left-[9px] top-5 w-4 h-4 rounded-full border-[3px] border-bg-deep flex items-center justify-center bg-current ${config.color}`} />
      
      <div 
        className={`glass-panel p-4 transition-colors ${hasDetails ? "cursor-pointer hover:bg-white/[0.03]" : ""}`}
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className={`text-sm ${config.color}`}>{config.icon}</span>
            <span className={`text-xs font-mono font-bold tracking-wider px-2 py-0.5 rounded-full bg-white/5 ${config.color}`}>
              {entry.event_type}
            </span>
          </div>
          <span className="text-[10px] font-mono text-white/40">
            {new Date(entry.timestamp).toLocaleString("en-US", { 
              month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" 
            })}
          </span>
        </div>
        
        <p className="text-sm text-white/90">{entry.action_taken}</p>
        
        {isComplianceFail && !expanded && (
          <p className="text-xs text-red-400 mt-2 font-mono flex items-center gap-1">
            <span>❌</span> Compliance Rejected. Click to view.
          </p>
        )}

        {hasDetails && (
          <div className={`mt-4 grid gap-4 overflow-hidden transition-all duration-300 ${expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
            <div className="min-h-0 space-y-4">
              
              {entry.agent_reasoning && (
                <div>
                  <p className="text-[10px] font-mono uppercase text-white/40 mb-1 flex items-center gap-1">
                    <span>🤖</span> AI Reasoning
                  </p>
                  <pre className="text-xs font-mono text-cyan-200 bg-cyan-950/30 p-3 rounded border border-cyan-500/20 whitespace-pre-wrap">
                    {entry.agent_reasoning}
                  </pre>
                </div>
              )}

              {isComplianceFail && entry.content_snapshot && (
                <ComplianceDiff 
                  originalContent={entry.content_snapshot}
                  reasoning={entry.agent_reasoning || "Failed compliance rules."}
                  ruleApplied={entry.rule_applied}
                  approvedContent={nextEntry?.content_snapshot || null}
                />
              )}

              {entry.content_snapshot && !isComplianceFail && (
                <div>
                  <p className="text-[10px] font-mono uppercase text-white/40 mb-1 flex items-center gap-1">
                    <span>📧</span> Email Content
                  </p>
                  <EmailPreview emailBody={entry.content_snapshot} />
                </div>
              )}
              
              {entry.rule_applied && !isComplianceFail && (
                <div>
                  <p className="text-[10px] font-mono uppercase text-white/40 mb-1 flex items-center gap-1">
                    <span>📜</span> Rule Applied
                  </p>
                  <div className="text-xs text-white/70 bg-white/5 px-3 py-2 rounded border border-white/10">
                    {entry.rule_applied}
                  </div>
                </div>
              )}

            </div>
          </div>
        )}
      </div>
    </div>
  );
}
