import EmailPreview from "./EmailPreview";

export default function ComplianceDiff({ 
  originalContent, 
  reasoning,
  ruleApplied,
  approvedContent
}: { 
  originalContent: string, 
  reasoning: string,
  ruleApplied: string | null,
  approvedContent?: string | null
}) {
  return (
    <div className="mt-3 bg-red-500/5 border border-red-500/20 rounded p-4">
      <div className="flex items-center gap-2 text-red-400 mb-2">
        <span>❌</span>
        <span className="font-bold text-sm">Compliance Check Failed</span>
      </div>
      
      <div className="text-sm text-white/80 mb-4 pl-6 border-l-2 border-red-500/30">
        <p className="mb-1">{reasoning}</p>
        {ruleApplied && (
          <p className="font-mono text-xs text-amber-400 mt-2 bg-amber-500/10 inline-block px-2 py-1 rounded">
            Violated: {ruleApplied}
          </p>
        )}
      </div>

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
    </div>
  );
}
