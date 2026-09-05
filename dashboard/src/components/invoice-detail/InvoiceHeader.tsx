import { Invoice } from "@/lib/types";
import StatusBadge from "@/components/invoices/StatusBadge";
import EscalationProgress from "@/components/invoices/EscalationProgress";

export default function InvoiceHeader({ invoice }: { invoice: Invoice }) {
  const overdueDays = invoice.due_date 
    ? Math.max(0, Math.floor((new Date().getTime() - new Date(invoice.due_date).getTime()) / (1000 * 3600 * 24)))
    : 0;

  return (
    <div className="glass-panel p-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/5 pb-4 mb-4">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">{invoice.client_name}</h2>
          <p className="text-sm text-white/50">{invoice.client_email}</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-mono font-bold text-white mb-1">
            ₹{invoice.amount.toLocaleString("en-IN")}
          </p>
          <p className={`text-sm font-mono ${overdueDays > 0 ? "text-amber-400" : "text-emerald-400"}`}>
            {overdueDays > 0 ? `${overdueDays} days overdue` : "Not overdue"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1.5">Status</p>
          <StatusBadge status={invoice.status} />
        </div>
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-2">Stage</p>
          <div className="flex items-center gap-2">
            <EscalationProgress stage={invoice.escalation_stage} />
            <span className="text-xs font-mono text-white/50">{invoice.escalation_stage || "None"}</span>
          </div>
        </div>
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">Promised Date</p>
          <p className="text-sm text-white/80">
            {invoice.promised_date ? new Date(invoice.promised_date).toLocaleDateString() : "None"}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase font-mono tracking-wider text-white/30 mb-1">Payment Options</p>
          {invoice.razorpay_payment_link_id ? (
            // The column stores a full URL today; tolerate a bare id too, so the
            // link is never rendered as https://rzp.io/l/https://rzp.io/l/...
            <a
              href={
                /^https?:\/\//.test(invoice.razorpay_payment_link_id)
                  ? invoice.razorpay_payment_link_id
                  : `https://rzp.io/l/${invoice.razorpay_payment_link_id}`
              }
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-[#00F0FF] hover:underline flex items-center gap-1"
            >
              Payment Link ↗
            </a>
          ) : <span className="text-xs text-white/30">No Link</span>}
          
          {invoice.razorpay_virtual_account_id && (
            <p className="text-xs text-white/50 mt-1" title="Virtual Account">
              VA: {invoice.razorpay_virtual_account_id}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
