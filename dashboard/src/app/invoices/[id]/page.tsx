"use client";
import { useApi } from "@/hooks/useApi";
import { Invoice } from "@/lib/types";
import InvoiceHeader from "@/components/invoice-detail/InvoiceHeader";
import AuditTimeline from "@/components/invoice-detail/AuditTimeline";
import DecisionExplorer from "@/components/invoice-detail/DecisionExplorer";
import RagContextPanel from "@/components/invoice-detail/RagContextPanel";
import ReplySimulator from "@/components/invoice-detail/ReplySimulator";
import QueryBoundary from "@/components/QueryBoundary";
import Link from "next/link";
import { use } from "react";

export default function InvoiceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const id = parseInt(resolvedParams.id, 10);

  const { data: invoice, error, isLoading, mutate } = useApi<Invoice>(`/api/invoices/${id}`);

  if (error || isLoading || !invoice) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Link
            href="/invoices"
            className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors"
          >
            ←
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">Invoice #{id}</h1>
        </div>
        <QueryBoundary
          error={error}
          loading={isLoading}
          onRetry={() => mutate()}
          loadingFallback={
            <div className="flex items-center justify-center min-h-[40vh]">
              <div className="flex items-center gap-3 text-white/50 font-mono">
                <div className="w-4 h-4 rounded-full border-2 border-white/20 border-t-accent-primary animate-spin" />
                Loading Invoice Details...
              </div>
            </div>
          }
        >
          {null}
        </QueryBoundary>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-4 mb-2">
        <Link 
          href="/invoices" 
          className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors"
        >
          ←
        </Link>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Invoice #{invoice.id}
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <InvoiceHeader invoice={invoice} />
          
          <DecisionExplorer invoiceId={id} />

          <div className="bg-white/[0.02] rounded-xl border border-white/5 p-6 shadow-inner">
            <AuditTimeline invoiceId={id} />
          </div>
        </div>
        
        <div className="lg:col-span-1 space-y-6 relative">
          <div className="sticky top-6 space-y-6">
            <RagContextPanel clientName={invoice.client_name} />
            <ReplySimulator invoiceId={id} />
          </div>
        </div>
      </div>
    </div>
  );
}
