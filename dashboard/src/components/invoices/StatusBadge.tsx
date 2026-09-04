import { STATUS_CONFIG } from "@/lib/constants";
import { InvoiceStatus } from "@/lib/types";

export default function StatusBadge({ status }: { status: InvoiceStatus }) {
  const config = STATUS_CONFIG[status] || { color: "text-gray-400", bg: "bg-gray-500/10", label: status, icon: "ℹ️" };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border border-white/5 whitespace-nowrap ${config.bg} ${config.color}`}>
      <span>{config.icon}</span>
      {config.label}
    </span>
  );
}
