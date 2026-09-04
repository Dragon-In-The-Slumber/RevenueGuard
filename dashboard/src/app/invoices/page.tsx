import InvoiceTable from "@/components/invoices/InvoiceTable";

export default function InvoicesPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Invoice Management</h1>
          <p className="text-white/50 text-sm font-mono max-w-2xl">
            Browse and filter through the complete portfolio of active and resolved invoices. Monitor AI escalation stages in real-time.
          </p>
        </div>
      </div>

      <InvoiceTable />
    </div>
  );
}
