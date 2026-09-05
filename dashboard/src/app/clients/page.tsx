"use client";
import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import ClientCard from "@/components/clients/ClientCard";
import RagSearchBar from "@/components/clients/RagSearchBar";
import ClientInvoiceList from "@/components/clients/ClientInvoiceList";
import QueryBoundary from "@/components/QueryBoundary";

interface ClientData {
  name: string;
  invoice_count: number;
  total_amount: number;
  recovered_amount: number;
  risk_level: string;
  tier: string;
  terms: string;
  contact: string;
}

export default function ClientsPage() {
  const { data, error, isLoading, mutate } = useApi<{ clients: ClientData[] }>("/api/clients");
  const clients = data?.clients || [];
  
  const [selectedClient, setSelectedClient] = useState<string | null>(null);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Client Intelligence Hub</h1>
        <p className="text-white/50 text-sm font-mono max-w-2xl">
          Deep strategic insights powered by RAG (ChromaDB). Monitor portfolio risk, query historical contract terms, and review client-specific guardrails.
        </p>
      </div>

      <QueryBoundary
        error={error}
        loading={isLoading}
        isEmpty={clients.length === 0}
        emptyMessage="No clients yet. Generate a batch from the Command Center."
        onRetry={() => mutate()}
        loadingFallback={
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="glass-panel h-40 animate-pulse" />
            ))}
          </div>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {clients.slice(0, 4).map((client) => (
            <ClientCard
              key={client.name}
              client={client}
              onClick={() => setSelectedClient(client.name)}
              isSelected={selectedClient === client.name}
            />
          ))}
        </div>
      </QueryBoundary>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RagSearchBar />
        
        {selectedClient ? (
          <ClientInvoiceList clientName={selectedClient} />
        ) : (
          <div className="glass-panel flex flex-col items-center justify-center p-8 text-center border-dashed border-white/20">
            <span className="text-4xl mb-4 opacity-50">🏢</span>
            <p className="text-white/50 font-mono text-sm">
              Select a client card above to view their active portfolio.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
