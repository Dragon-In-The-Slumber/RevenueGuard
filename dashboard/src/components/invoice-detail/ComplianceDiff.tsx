import EmailPreview from "./EmailPreview";
import { COMPLIANCE_CONFIG, VERDICT_SOURCE_LABEL } from "@/lib/constants";

/**
 * Renders one compliance outcome.
 *
 * FAIL is a two-pane diff: the rejected draft beside the approved rewrite.
 * UNREVIEWED has no second pane — nothing was rejected, so nothing was
 * redrafted; the draft simply went out without a judge seeing it. Showing it in
 * the red "Compliance Check Failed" frame would misrepresent an outage as a
 * content violation.
 */
export default function ComplianceDiff({
  originalContent,
  reasoning,
  ruleApplied,
  approvedContent,
  verdict = "FAIL",
  verdictSource,
}: {
  originalContent: string;
  reasoning: string;
  ruleApplied: string | null;
  approvedContent?: string | null;
  verdict?: string;
  verdictSource?: string | null;
}) {
  const config = COMPLIANCE_CONFIG[verdict] ?? COMPLIANCE_CONFIG.FAIL;
  const isUnreviewed = verdict === "UNREVIEWED";

  return (
    <div className={`mt-3 rounded p-4 border ${config.bg} ${config.border}`}>
      <div className={`flex items-center gap-2 mb-2 ${config.color}`}>
        <span>{config.icon}</span>
        <span className="font-bold text-sm">
          {isUnreviewed ? "Sent Without Compliance Review" : "Compliance Check Failed"}
        </span>
        {verdictSource && (
          <span className="ml-auto text-[10px] font-mono uppercase tracking-wider text-white/30">
            {VERDICT_SOURCE_LABEL[verdictSource] ?? verdictSource}
          </span>
        )}
      </div>

      <div className={`text-sm text-white/80 mb-4 pl-6 border-l-2 ${config.border}`}>
        <p className="mb-1">{reasoning}</p>
        {ruleApplied && (
          <p className={`font-mono text-xs mt-2 inline-block px-2 py-1 rounded ${config.bg} ${config.color}`}>
            {isUnreviewed ? "Reason: " : "Violated: "}{ruleApplied}
          </p>
        )}
        {isUnreviewed && (
          <p className="text-xs text-white/50 mt-2">
            The draft was delivered. It is counted as neither a pass nor a failure,
            and is excluded from the compliance rate.
          </p>
        )}
      </div>

      {isUnreviewed ? (
        /* Single pane: there is no rewrite to compare against. */
        <div>
          <p className="text-xs font-mono uppercase text-white/40 mb-2">Draft as sent:</p>
          <EmailPreview emailBody={originalContent} />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-mono uppercase text-white/40 mb-2">Original Rejected Draft:</p>
            <div className="opacity-80 grayscale">
              <EmailPreview emailBody={originalContent} />
            </div>
          </div>

          {approvedContent && (
            <div>
              <p className="text-xs font-mono uppercase text-emerald-400/80 mb-2 flex items-center gap-1">
                <span>✅</span> Approved Rewrite:
              </p>
              <EmailPreview emailBody={approvedContent} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
