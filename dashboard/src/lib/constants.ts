export const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string; icon: string }> = {
  ISSUED:           { color: "text-blue-400",    bg: "bg-blue-500/10",    label: "Issued",           icon: "📄" },
  OVERDUE:          { color: "text-amber-400",   bg: "bg-amber-500/10",   label: "Overdue",          icon: "⏰" },
  NOTIFIED_1:       { color: "text-cyan-400",    bg: "bg-cyan-500/10",    label: "Stage 1 Sent",     icon: "📧" },
  NOTIFIED_2:       { color: "text-purple-400",  bg: "bg-purple-500/10",  label: "Stage 2 Sent",     icon: "📧" },
  NOTIFIED_3:       { color: "text-orange-400",  bg: "bg-orange-500/10",  label: "Stage 3 Sent",     icon: "📱" },
  PAUSED_PTP:       { color: "text-yellow-400",  bg: "bg-yellow-500/10",  label: "Promise to Pay",   icon: "🤝" },
  DISPUTE:          { color: "text-red-400",     bg: "bg-red-500/10",     label: "Disputed",         icon: "⚔️" },
  LEGAL_HOLD:       { color: "text-red-500",     bg: "bg-red-600/10",     label: "Legal Hold",       icon: "🚫" },
  UNRESPONSIVE:     { color: "text-gray-400",    bg: "bg-gray-500/10",    label: "Unresponsive",     icon: "👻" },
  RECOVERED:        { color: "text-emerald-400", bg: "bg-emerald-500/10", label: "Recovered",        icon: "✅" },
  HUMAN_ESCALATED:  { color: "text-pink-400",    bg: "bg-pink-500/10",    label: "Human Escalated",  icon: "👤" },
};

export const EVENT_TYPE_CONFIG: Record<string, { color: string; icon: string }> = {
  EMAIL_SENT:          { color: "text-emerald-400", icon: "📧" },
  INTENT_CLASSIFIED:   { color: "text-cyan-400",    icon: "🤖" },
  STATUS_CHANGED:      { color: "text-amber-400",   icon: "🔄" },
  ESCALATION_BLOCKED:  { color: "text-red-400",     icon: "🛑" },
  COMPLIANCE_PASSED:   { color: "text-emerald-400", icon: "✅" },
  COMPLIANCE_FAILED:   { color: "text-red-400",     icon: "❌" },
  TOOL_CALL:           { color: "text-purple-400",  icon: "🔧" },
  HUMAN_ESCALATED:     { color: "text-pink-400",    icon: "👤" },
  PAYMENT_RECEIVED:    { color: "text-emerald-400", icon: "💰" },
};
